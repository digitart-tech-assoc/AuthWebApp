"""役割: ロール定義・割り当ての変更履歴（role_audit_logs）の記録

DB への変更は、変更と同じトランザクション（呼び出し元のカーソル）で insert_audit_logs を呼ぶ。記録に失敗したら変更も失敗させる。
Discord への変更は、API 呼び出しが成功するたびに record_discord_audit_safely で記録する。記録に失敗しても元の処理は続ける。
値の定義は docs/db.md の role_audit_logs を参照。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, replace
from typing import Any, Iterable

from fastapi import Depends

from app.core.auth import get_current_principal
from app.db.connection import _connect

logger = logging.getLogger(__name__)

INTERNAL_SERVICE_SUB = "internal-service"

# operation
OP_MANIFEST_PATCH = "manifest_patch"
OP_MANIFEST_PUT = "manifest_put"
OP_PUSH = "push"
OP_SELF_BATCH = "self_batch"
OP_JOIN_OTP_VERIFY = "join_otp_verify"
OP_STUDENT_PROFILE = "student_profile"
OP_PRE_MEMBER_REGISTER = "pre_member_register"

# system
SYSTEM_DB = "db"
SYSTEM_DISCORD = "discord"

# target_type
TARGET_CATEGORY = "category"
TARGET_ROLE = "role"
TARGET_ROLE_ASSIGNMENT = "role_assignment"
TARGET_MEMBER_ROLES = "member_roles"

# action
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_RENAME_ID = "rename_id"
ACTION_REORDER = "reorder"
ACTION_ROLLBACK = "rollback"


@dataclass(frozen=True)
class AuditContext:
	"""1回の API 呼び出しで書く監査ログに共通する値。"""

	request_id: str
	actor_sub: str | None
	actor_discord_id: str | None
	operation: str = ""

	def with_operation(self, operation: str) -> "AuditContext":
		return replace(self, operation=operation)


@dataclass(frozen=True)
class AuditLog:
	"""role_audit_logs の1行分（AuditContext に含まれない値）。"""

	system: str
	target_type: str
	target_id: str
	action: str
	before: dict[str, Any] | None = None
	after: dict[str, Any] | None = None


def _normalize(field: str, value: Any) -> Any:
	# permissions は DB では BIGINT、Discord の応答では文字列のことがあるため、int にそろえて比べる
	if field == "permissions" and value is not None:
		return int(value)
	return value


def diff_fields(
	before: dict[str, Any] | None,
	after: dict[str, Any] | None,
	fields: Iterable[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None] | None:
	"""変更前後の行を比べ、変わったフィールドだけを (before, after) で返す。変化がなければ None を返す。

	作成（before が None）は after に全フィールドを入れ、削除（after が None）は before に全フィールドを入れる。
	"""
	fields = list(fields)
	if before is None and after is None:
		return None
	if before is None:
		return None, {f: _normalize(f, after.get(f)) for f in fields}
	if after is None:
		return {f: _normalize(f, before.get(f)) for f in fields}, None
	changed = [f for f in fields if _normalize(f, before.get(f)) != _normalize(f, after.get(f))]
	if not changed:
		return None
	return (
		{f: _normalize(f, before.get(f)) for f in changed},
		{f: _normalize(f, after.get(f)) for f in changed},
	)


def assignment_diff(added: Iterable[str], removed: Iterable[str]) -> dict[str, list[str]] | None:
	"""割り当ての差分を after に入れる形（{"added": [...], "removed": [...]}）にする。差分がなければ None を返す。"""
	added_list = sorted(added)
	removed_list = sorted(removed)
	if not added_list and not removed_list:
		return None
	return {"added": added_list, "removed": removed_list}


def _dump(value: dict[str, Any] | None) -> str | None:
	return None if value is None else json.dumps(value, ensure_ascii=False)


def insert_audit_logs(cur: Any, audit: AuditContext | None, logs: Iterable[AuditLog]) -> None:
	"""呼び出し元のカーソルで監査ログを書き込む。audit が None なら何もしない。"""
	if audit is None:
		return
	logs = list(logs)
	if not logs:
		return
	for log in logs:
		cur.execute(
			"""
			INSERT INTO role_audit_logs
			(request_id, operation, system, target_type, target_id, action, before, after, actor_sub, actor_discord_id)
			VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
			""",
			(
				audit.request_id,
				audit.operation,
				log.system,
				log.target_type,
				log.target_id,
				log.action,
				_dump(log.before),
				_dump(log.after),
				audit.actor_sub,
				audit.actor_discord_id,
			),
		)
	logger.info(
		"role audit: request_id=%s operation=%s system=%s rows=%d",
		audit.request_id,
		audit.operation,
		",".join(sorted({log.system for log in logs})),
		len(logs),
	)


def record_audit_logs(audit: AuditContext | None, logs: Iterable[AuditLog]) -> None:
	"""接続を取得して監査ログを書き込む（Discord への変更の記録用）。"""
	logs = list(logs)
	if audit is None or not logs:
		return
	with _connect() as conn:
		with conn.cursor() as cur:
			insert_audit_logs(cur, audit, logs)
		conn.commit()


async def record_discord_audit_safely(audit: AuditContext | None, logs: Iterable[AuditLog]) -> None:
	"""Discord への変更を記録する。記録に失敗しても例外を出さず、元の処理を続けさせる。"""
	logs = list(logs)
	if audit is None or not logs:
		return
	try:
		await asyncio.to_thread(record_audit_logs, audit, logs)
	except Exception as exc:
		# DB の例外メッセージには値が含まれることがあるため、型名だけを出す
		logger.error(
			"Failed to record role audit logs: request_id=%s operation=%s rows=%d (%s)",
			audit.request_id,
			audit.operation,
			len(logs),
			type(exc).__name__,
		)


def get_audit_context(principal: dict = Depends(get_current_principal)) -> AuditContext:
	"""FastAPI の依存関数。リクエストごとに request_id を作り、操作した人の ID を入れる。認可は行わない。"""
	return AuditContext(
		request_id=str(uuid.uuid4()),
		actor_sub=principal.get("sub"),
		actor_discord_id=principal.get("discord_id"),
	)


def internal_audit_context(operation: str) -> AuditContext:
	"""SHARED_SECRET で認証する内部呼び出し用の AuditContext を作る。"""
	return AuditContext(
		request_id=str(uuid.uuid4()),
		actor_sub=INTERNAL_SERVICE_SUB,
		actor_discord_id=None,
		operation=operation,
	)
