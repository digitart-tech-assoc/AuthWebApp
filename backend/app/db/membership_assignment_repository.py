"""役割: 管理画面の割当の保存に合わせて、会員種別（user_memberships）を更新する（#251）

会員種別のロール（member / sub_user / obog / pre_member）は user_memberships を正とし、
管理画面の割当の保存（PUT / PATCH /api/v1/manifest）を変更の入口とする。
割当の保存と同じトランザクションで、種別のロールの割当が実際に変わった人の、変わった種別の行だけを更新する。

- admin の行は保存では変更しない（admin ロールは Discord で直接付け外しし、sync で取り込む）
- 1 種別に複数のロールがある場合（MEMBER_ROLE_IDS など）、すべてを持つときだけその種別とし、一部だけ持つ状態にする保存は拒否する
- member と sub垢 の両方、または pre-member と member / sub垢 の両方を持つ状態にする保存は拒否する
"""

from __future__ import annotations

from typing import Any

from app.core.config import MembershipType
from app.core.exceptions import MembershipAssignmentError
from app.core.membership_roles import membership_role_ids
from app.db.audit_repository import (
	ACTION_UPDATE,
	SYSTEM_DB,
	TARGET_MEMBERSHIP,
	AuditContext,
	AuditLog,
	assignment_diff,
	insert_audit_logs,
)

# 保存で更新する種別（admin は含めない）
SAVE_MANAGED_TYPES: tuple[str, ...] = (
	MembershipType.MEMBER,
	MembershipType.SUB_USER,
	MembershipType.OBOG,
	MembershipType.PRE_MEMBER,
)

# 同時に持つ状態にする保存を拒否する種別の組
EXCLUSIVE_TYPE_PAIRS: tuple[tuple[str, str], ...] = (
	(MembershipType.MEMBER, MembershipType.SUB_USER),
	(MembershipType.PRE_MEMBER, MembershipType.MEMBER),
	(MembershipType.PRE_MEMBER, MembershipType.SUB_USER),
)


def save_managed_role_types() -> dict[str, str]:
	"""保存で種別を更新するロールの ID -> 種別 を返す（環境変数を呼び出しのたびに読む）。"""
	configured = membership_role_ids()
	return {role_id: m_type for m_type in SAVE_MANAGED_TYPES for role_id in configured[m_type]}


def membership_audit_logs(discord_id: str, added: list[str], removed: list[str]) -> list[AuditLog]:
	"""1 人分の種別の追加・削除（実際に変わったもの）を監査ログにする。変更がなければ空。"""
	after = assignment_diff(added, removed)
	if after is None:
		return []
	return [AuditLog(SYSTEM_DB, TARGET_MEMBERSHIP, discord_id, ACTION_UPDATE, None, after)]


def apply_membership_changes(
	cur: Any,
	changes: dict[str, tuple[list[str], list[str]]],
	audit: AuditContext | None = None,
) -> dict[str, tuple[list[str], list[str]]]:
	"""割当の変更（replace_role_assignments の戻り値）に合わせて、呼び出し元のトランザクションで user_memberships を更新する。

	種別として成り立たない状態になる場合は MembershipAssignmentError を送出する（呼び出し元でロールバックする）。
	Discord ID -> (追加した種別, 削除した種別) を返す（実際に変わったものだけ）。
	"""
	role_types = save_managed_role_types()
	type_role_ids: dict[str, set[str]] = {m_type: set() for m_type in SAVE_MANAGED_TYPES}
	for role_id, m_type in role_types.items():
		type_role_ids[m_type].add(role_id)

	# Discord ID -> 割当が変わった種別
	changed_types: dict[str, set[str]] = {}
	for role_id, (added, removed) in changes.items():
		m_type = role_types.get(role_id)
		if m_type is None:
			continue
		for discord_id in (*added, *removed):
			changed_types.setdefault(discord_id, set()).add(m_type)

	result: dict[str, tuple[list[str], list[str]]] = {}
	logs: list[AuditLog] = []
	assigned_by = audit.actor_discord_id if audit is not None else None
	# 同じ人の種別を変える保存同士を直列化する（別のロールの保存が並行すると、互いの変更が見えずに排他の判定を通るため）。
	# デッドロックを避けるため、Discord ID の順にロックする
	for discord_id in sorted(changed_types):
		cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"membership:{discord_id}",))
	for discord_id in sorted(changed_types):
		types = changed_types[discord_id]
		cur.execute("SELECT role_id FROM role_member_assignments WHERE user_id = %s", (discord_id,))
		held = {row[0] for row in cur.fetchall()}
		held_counts = {m_type: len(ids & held) for m_type, ids in type_role_ids.items()}
		cur.execute("SELECT membership_type FROM user_memberships WHERE discord_id = %s", (discord_id,))
		rows = {row[0] for row in cur.fetchall()}
		# 種別を持つか: 割当が変わった種別は保存後の割当で、変わっていない種別は割当または行で判断する
		# （行だけあり割当がない人に、同時に持てない種別を付けさせないため）
		has_type = {
			m_type: held_counts[m_type] > 0 or (m_type not in types and m_type in rows)
			for m_type in SAVE_MANAGED_TYPES
		}

		for m_type in sorted(types):
			if 0 < held_counts[m_type] < len(type_role_ids[m_type]):
				raise MembershipAssignmentError(MembershipAssignmentError.PARTIAL, discord_id, (m_type,))
		for first, second in EXCLUSIVE_TYPE_PAIRS:
			if (first in types or second in types) and has_type[first] and has_type[second]:
				raise MembershipAssignmentError(MembershipAssignmentError.EXCLUSIVE, discord_id, (first, second))

		added_types: list[str] = []
		removed_types: list[str] = []
		for m_type in sorted(types):
			if held_counts[m_type] > 0:
				cur.execute(
					"""
					INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
					VALUES (%s, %s, %s, now(), now())
					ON CONFLICT (discord_id, membership_type) DO NOTHING
					""",
					(discord_id, m_type, assigned_by),
				)
				if cur.rowcount > 0:
					added_types.append(m_type)
			else:
				cur.execute(
					"DELETE FROM user_memberships WHERE discord_id = %s AND membership_type = %s",
					(discord_id, m_type),
				)
				if cur.rowcount > 0:
					removed_types.append(m_type)
		if added_types or removed_types:
			result[discord_id] = (added_types, removed_types)
			logs.extend(membership_audit_logs(discord_id, added_types, removed_types))

	insert_audit_logs(cur, audit, logs)
	return result
