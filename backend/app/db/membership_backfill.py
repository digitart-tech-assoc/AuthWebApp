"""役割: 会員種別（user_memberships）とロールの割当（role_member_assignments）の既存データの整理（#251 段階 4）

管理画面の保存で user_memberships を更新するようになる前のデータには、次の食い違いが残っている。
#173 の修正（push 後の Bot の reconcile が届くようになる）より前に、scripts/fix_membership_assignments.py で整理する。

1. sub垢 と member の両方を持つ人（sub_user の行または sub垢 の割当があり、member の割当もある）
   - member ロールの割当を外す。sub_user の行があれば member の行も消す（sub_user を正とする）
   - 割当を外したあとの push で、Discord の member ロールも外れる。sub垢 を外す前に行う
     （member ロールが残っていると、sync で member の行が作られるため）
2. 行はあるが割当がない人（member / sub_user / obog / pre_member）
   - その種別のロールの割当を追加する。割当がないと、push のたびに Discord のロールが外され、reconcile で付け直される
   - member の割当は、sub_user の行または sub垢 の割当がある人には補完しない（1 で外すため）。
     sub垢 の割当があり、sub_user の行がなく member の行だけがある人は件数だけ数える（先に sync で揃える）
   - 補完すると同時に持てない組（member と sub垢、pre-member と member / sub垢）になる場合は補完せず、件数だけ数える
     （例: OTP 検証済みでプロフィール未送信の、pre_member の行と member の割当を持つ人）
3. 割当はあるが行がない人は、変更せず件数だけ数える（どちらを正とするか決められないため）

admin の行と admin ロールの割当は扱わない（Discord で直接付け外しし、sync で取り込む）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import MembershipType
from app.core.membership_roles import membership_role_ids
from app.db.audit_repository import AuditContext, insert_audit_logs
from app.db.guild_repository import member_roles_audit_logs
from app.db.connection import limit_lock_wait
from app.db.membership_assignment_repository import EXCLUSIVE_TYPE_PAIRS, SAVE_MANAGED_TYPES, membership_audit_logs

MEMBER = MembershipType.MEMBER
SUB_USER = MembershipType.SUB_USER
PRE_MEMBER = MembershipType.PRE_MEMBER


# 両テーブルのロックを待つ上限（ミリ秒）。超えたら何もせずに終わる（時間をおいて再実行する）
BACKFILL_LOCK_TIMEOUT_MS = 5000


class BackfillLockTimeoutError(RuntimeError):
	"""ほかのトランザクションが終わらず、整理に必要なロックを取れなかった。"""

	def __init__(self) -> None:
		super().__init__("Could not lock user_memberships / role_member_assignments. Run again later.")


@dataclass
class BackfillPlan:
	"""整理で行う変更と、変更しない食い違いの件数。"""

	# (role_id, discord_id)
	add_assignments: list[tuple[str, str]] = field(default_factory=list)
	remove_assignments: list[tuple[str, str]] = field(default_factory=list)
	# (discord_id, membership_type)
	remove_memberships: list[tuple[str, str]] = field(default_factory=list)
	# 種別 -> 補完すると同時に持てない組になるため補完しなかった行の数
	skipped_conflicting_rows: dict[str, int] = field(default_factory=dict)
	# sub垢 の割当はあるが sub_user の行がなく、member の行だけがある人の数（先に sync で sub_user に揃える）
	member_rows_of_sub_role_holders: int = 0
	# 種別 -> 割当はあるが行がない人の数
	assignments_without_row: dict[str, int] = field(default_factory=dict)

	def summary(self) -> dict[str, Any]:
		"""件数だけの要約（Discord ID は含めない）。"""
		return {
			"add_assignments": len(self.add_assignments),
			"remove_assignments": len(self.remove_assignments),
			"remove_memberships": len(self.remove_memberships),
			"users_changed": len({d for _, d in self.add_assignments + self.remove_assignments} | {d for d, _ in self.remove_memberships}),
			"skipped_conflicting_rows": dict(sorted(self.skipped_conflicting_rows.items())),
			"member_rows_of_sub_role_holders": self.member_rows_of_sub_role_holders,
			"assignments_without_row": dict(sorted(self.assignments_without_row.items())),
		}


def plan_backfill(
	memberships: set[tuple[str, str]],
	assignments: set[tuple[str, str]],
	type_role_ids: dict[str, tuple[str, ...]],
) -> BackfillPlan:
	"""現在の行と割当から、整理で行う変更を決める（DB には触れない）。

	memberships: (discord_id, membership_type) の集合。assignments: (role_id, discord_id) の集合。
	type_role_ids: 種別 -> ロール ID（membership_role_ids() の戻り値）。
	"""
	plan = BackfillPlan()
	rows_by_user: dict[str, set[str]] = {}
	for discord_id, m_type in memberships:
		rows_by_user.setdefault(discord_id, set()).add(m_type)
	held_by_user: dict[str, set[str]] = {}
	for role_id, discord_id in assignments:
		held_by_user.setdefault(discord_id, set()).add(role_id)

	member_roles = set(type_role_ids.get(MEMBER, ()))
	sub_roles = set(type_role_ids.get(SUB_USER, ()))

	# sub_user の行または sub垢 の割当がある人
	sub_users = {
		discord_id
		for discord_id in set(rows_by_user) | set(held_by_user)
		if SUB_USER in rows_by_user.get(discord_id, set()) or held_by_user.get(discord_id, set()) & sub_roles
	}

	# 1. sub垢 と member の両方を持つ人
	if member_roles:
		for discord_id in sorted(sub_users):
			rows = rows_by_user.get(discord_id, set())
			held = held_by_user.get(discord_id, set())
			for role_id in sorted(held & member_roles):
				plan.remove_assignments.append((role_id, discord_id))
			if SUB_USER in rows and MEMBER in rows:
				plan.remove_memberships.append((discord_id, MEMBER))
	removed_rows = set(plan.remove_memberships)
	removed_assignments = set(plan.remove_assignments)

	# 2. 行はあるが割当がない人。補完すると同時に持てない組（PR A の保存と同じ規則）になる場合は補完せず、件数だけ数える
	remaining_held: dict[str, set[str]] = {discord_id: set(held) for discord_id, held in held_by_user.items()}
	for role_id, discord_id in removed_assignments:
		remaining_held[discord_id].discard(role_id)
	role_type = {role_id: m_type for m_type in SAVE_MANAGED_TYPES for role_id in type_role_ids.get(m_type, ())}
	for discord_id, m_type in sorted(memberships - removed_rows):
		if m_type not in SAVE_MANAGED_TYPES:
			continue
		if m_type == MEMBER and discord_id in sub_users:
			# member の割当は 1 で外した（または補完しない）。member の行だけが残る人は sync で sub_user に揃える
			if (discord_id, MEMBER) not in removed_rows and SUB_USER not in rows_by_user[discord_id]:
				plan.member_rows_of_sub_role_holders += 1
			continue
		held = remaining_held.get(discord_id, set())
		missing = sorted(set(type_role_ids.get(m_type, ())) - held)
		if not missing:
			continue
		remaining_rows = {t for t in rows_by_user[discord_id] if (discord_id, t) not in removed_rows}
		other_types = {role_type[r] for r in held if r in role_type} | (remaining_rows - {m_type})
		if any(m_type in pair and (set(pair) - {m_type}) & other_types for pair in EXCLUSIVE_TYPE_PAIRS):
			plan.skipped_conflicting_rows[m_type] = plan.skipped_conflicting_rows.get(m_type, 0) + 1
			continue
		for role_id in missing:
			plan.add_assignments.append((role_id, discord_id))

	# 3. 割当はあるが行がない人（変更しない）
	remaining = assignments - removed_assignments
	for m_type in SAVE_MANAGED_TYPES:
		roles = set(type_role_ids.get(m_type, ()))
		users = {d for r, d in remaining if r in roles}
		without_row = {d for d in users if (d, m_type) not in memberships or (d, m_type) in removed_rows}
		if without_row:
			plan.assignments_without_row[m_type] = len(without_row)
	return plan


def _load(cur: Any) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
	cur.execute("SELECT discord_id, membership_type FROM user_memberships")
	memberships = {(row[0], row[1]) for row in cur.fetchall()}
	cur.execute("SELECT role_id, user_id FROM role_member_assignments")
	assignments = {(row[0], row[1]) for row in cur.fetchall()}
	return memberships, assignments


def run_backfill(conn: Any, *, apply: bool, audit: AuditContext | None = None) -> BackfillPlan:
	"""整理を計画し、apply が True のときだけ 1 つのトランザクションで反映する。

	apply が False のときは何も書き込まない（ロールバックする）。反映した変更は監査ログに記録する。
	"""
	with conn.cursor() as cur:
		# 計画から反映までの間に管理画面の保存などで変わらないよう、両テーブルをロックする
		# 管理画面の保存（割当 → 種別の行の順に変える）と同じ順でロックし、待ち時間に上限を設ける
		if apply:
			with limit_lock_wait(cur, BACKFILL_LOCK_TIMEOUT_MS, BackfillLockTimeoutError):
				cur.execute("LOCK TABLE role_member_assignments, user_memberships IN SHARE ROW EXCLUSIVE MODE")
		memberships, assignments = _load(cur)
		plan = plan_backfill(memberships, assignments, membership_role_ids())
		if not apply:
			conn.rollback()
			return plan

		added_by_user: dict[str, list[str]] = {}
		removed_by_user: dict[str, list[str]] = {}
		for role_id, discord_id in plan.remove_assignments:
			cur.execute(
				"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
				(role_id, discord_id),
			)
			if cur.rowcount > 0:
				removed_by_user.setdefault(discord_id, []).append(role_id)
		for role_id, discord_id in plan.add_assignments:
			cur.execute(
				"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
				(role_id, discord_id),
			)
			if cur.rowcount > 0:
				added_by_user.setdefault(discord_id, []).append(role_id)
		removed_types: dict[str, list[str]] = {}
		for discord_id, m_type in plan.remove_memberships:
			cur.execute(
				"DELETE FROM user_memberships WHERE discord_id = %s AND membership_type = %s",
				(discord_id, m_type),
			)
			if cur.rowcount > 0:
				removed_types.setdefault(discord_id, []).append(m_type)

		logs = []
		for discord_id in sorted(set(added_by_user) | set(removed_by_user)):
			logs.extend(member_roles_audit_logs(
				discord_id, added_by_user.get(discord_id, []), removed_by_user.get(discord_id, []),
			))
		for discord_id in sorted(removed_types):
			logs.extend(membership_audit_logs(discord_id, [], removed_types[discord_id]))
		insert_audit_logs(cur, audit, logs)
	conn.commit()
	return plan
