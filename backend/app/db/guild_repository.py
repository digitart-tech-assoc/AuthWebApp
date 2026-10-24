"""役割: ギルドメンバーおよびロール割り当てに関する永続化処理"""

from __future__ import annotations

import logging
from typing import Any

from app.db.audit_repository import (
	ACTION_UPDATE,
	SYSTEM_DB,
	TARGET_MEMBER_ROLES,
	AuditContext,
	AuditLog,
	assignment_diff,
	insert_audit_logs,
)
from app.db.connection import _connect

logger = logging.getLogger(__name__)


def member_roles_audit_logs(user_id: str, added: list[str], removed: list[str]) -> list[AuditLog]:
	"""メンバー単位のロール割り当ての変更（実際に追加・削除したもの）を監査ログにする。変更がなければ空。"""
	after = assignment_diff(added, removed)
	if after is None:
		return []
	return [AuditLog(SYSTEM_DB, TARGET_MEMBER_ROLES, user_id, ACTION_UPDATE, None, after)]


def save_guild_members(members: list[dict[str, Any]]) -> None:
	"""Discordから取得したギルドメンバーを保存/更新する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			for m in members:
				cur.execute(
					"""
					INSERT INTO guild_members (user_id, username, display_name, avatar)
					VALUES (%s, %s, %s, %s)
					ON CONFLICT (user_id) DO UPDATE SET
						username = EXCLUDED.username,
						display_name = EXCLUDED.display_name,
						avatar = EXCLUDED.avatar,
						updated_at = now()
					""",
					(m["user_id"], m["username"], m.get("display_name"), m.get("avatar")),
				)
		conn.commit()


def replace_role_assignments(cur: Any, assignments: dict[str, list[str]]) -> dict[str, tuple[list[str], list[str]]]:
	"""呼び出し元のトランザクションで、指定されたロールの割り当てを送られたメンバー一覧に置き換える。

	全件を削除して入れ直すのではなく、外すメンバーだけを DELETE、足すメンバーだけを INSERT する。
	role_id -> (実際に追加したメンバー, 実際に削除したメンバー) を返す（rowcount > 0 のものだけ）。
	"""
	changes: dict[str, tuple[list[str], list[str]]] = {}
	for role_id, user_ids in assignments.items():
		cur.execute(
			"SELECT user_id FROM role_member_assignments WHERE role_id = %s FOR UPDATE",
			(role_id,),
		)
		current = {row[0] for row in cur.fetchall()}
		desired = set(user_ids)
		added: list[str] = []
		removed: list[str] = []
		for user_id in sorted(current - desired):
			cur.execute(
				"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
				(role_id, user_id),
			)
			if cur.rowcount > 0:
				removed.append(user_id)
		for user_id in sorted(desired - current):
			cur.execute(
				"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
				(role_id, user_id),
			)
			if cur.rowcount > 0:
				added.append(user_id)
		changes[role_id] = (added, removed)
	return changes


def save_role_assignments(assignments: dict[str, list[str]]) -> None:
	"""
	role_id -> [user_id, ...] のマッピングでロール割り当てを置き換え保存（差分だけを更新する）。
	assignments に含まれる role_id の割り当てのみ上書き。含まれない role_id は触らない。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			changes = replace_role_assignments(cur, assignments)
		conn.commit()
	logger.info(
		"save_role_assignments completed: %d roles, %d added, %d removed",
		len(assignments),
		sum(len(added) for added, _ in changes.values()),
		sum(len(removed) for _, removed in changes.values()),
	)


def add_user_to_role(user_id: str, role_id: str, audit: AuditContext | None = None) -> None:
	"""特定ユーザーをロールに追加する（重複チェック付き）。実際に追加したときだけ監査ログに記録する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
				(role_id, user_id),
			)
			if cur.rowcount > 0:
				insert_audit_logs(cur, audit, member_roles_audit_logs(user_id, [role_id], []))
			conn.commit()


def remove_user_from_role(user_id: str, role_id: str, audit: AuditContext | None = None) -> None:
	"""特定ユーザーをロールから削除する。実際に削除したときだけ監査ログに記録する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
				(role_id, user_id),
			)
			if cur.rowcount > 0:
				insert_audit_logs(cur, audit, member_roles_audit_logs(user_id, [], [role_id]))
			conn.commit()


def batch_update_user_roles(
	user_id: str,
	roles_to_add: list[str],
	roles_to_remove: list[str],
	audit: AuditContext | None = None,
) -> None:
	"""1ユーザーのロール割り当てを一括で追加/削除する（1トランザクション）。

	Args:
		user_id:        対象ユーザーの Discord ID
		roles_to_add:   追加するロール ID リスト
		roles_to_remove: 削除するロール ID リスト
		audit:          渡すと、実際に追加・削除したロールを同じトランザクションで監査ログに記録する
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# 同一ユーザーのDB更新を同時に行う処理間で直列化する。
			cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"self-role:{user_id}",))
			added: list[str] = []
			removed: list[str] = []
			for role_id in roles_to_remove:
				cur.execute(
					"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
					(role_id, user_id),
				)
				if cur.rowcount > 0:
					removed.append(role_id)
			for role_id in roles_to_add:
				cur.execute(
					"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
					(role_id, user_id),
				)
				if cur.rowcount > 0:
					added.append(role_id)
			insert_audit_logs(cur, audit, member_roles_audit_logs(user_id, added, removed))
		conn.commit()
		logger.info(
			"batch_update_user_roles: added=%s removed=%s",
			roles_to_add,
			roles_to_remove,
		)


def fetch_guild_members() -> list[dict[str, Any]]:
	"""保存済みのギルドメンバー一覧を取得。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("SELECT user_id, username, display_name, avatar FROM guild_members ORDER BY username ASC")
			return [
				{"user_id": row[0], "username": row[1], "display_name": row[2], "avatar": row[3]}
				for row in cur.fetchall()
			]


def fetch_role_assignments() -> dict[str, list[str]]:
	"""全ロール割り当てを {role_id: [user_id, ...]} 形式で取得。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("SELECT role_id, user_id FROM role_member_assignments")
			result: dict[str, list[str]] = {}
			for role_id, user_id in cur.fetchall():
				result.setdefault(role_id, []).append(user_id)
			return result


def fetch_role_assignments_for_user(user_id: str) -> dict[str, list[str]]:
	"""指定ユーザー自身のロール割り当てだけを取得。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"SELECT role_id, user_id FROM role_member_assignments WHERE user_id = %s",
				(user_id,),
			)
			result: dict[str, list[str]] = {}
			for role_id, assigned_user_id in cur.fetchall():
				result.setdefault(role_id, []).append(assigned_user_id)
			return result
