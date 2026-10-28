"""役割: ロールマニフェストおよびロールカテゴリに関する永続化処理"""

from __future__ import annotations

from typing import Any

from app.db.audit_repository import (
	ACTION_CREATE,
	ACTION_DELETE,
	ACTION_RENAME_ID,
	ACTION_UPDATE,
	SYSTEM_DB,
	TARGET_CATEGORY,
	TARGET_ROLE,
	TARGET_ROLE_ASSIGNMENT,
	AuditContext,
	AuditLog,
	assignment_diff,
	diff_fields,
	insert_audit_logs,
)
from app.db.connection import _connect
from app.db.guild_repository import replace_role_assignments

# 監査ログで比べるフィールド（updated_at・is_managed_by_app は含めない）
CATEGORY_AUDIT_FIELDS = ("name", "display_order", "is_collapsed", "permissions", "is_restricted")
ROLE_AUDIT_FIELDS = ("name", "color", "hoist", "mentionable", "permissions", "position", "category_id", "is_our_bot")


def fetch_manifest() -> dict[str, list[dict[str, Any]]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, display_order, is_collapsed, COALESCE(permissions, 0), COALESCE(is_restricted, FALSE)
                FROM role_categories
                ORDER BY display_order ASC, name ASC
                """
            )
            categories = [
                {
                    "id": row[0],
                    "name": row[1],
                    "display_order": row[2],
                    "is_collapsed": row[3],
                    "permissions": int(row[4]),
                    "is_restricted": bool(row[5]),
                }
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT role_id, name, color, hoist, mentionable, permissions, position, category_id, is_our_bot
                FROM role_manifests
                ORDER BY position DESC, name ASC
                """
            )
            roles = [
                {
                    "role_id": row[0],
                    "name": row[1],
                    "color": row[2],
                    "hoist": row[3],
                    "mentionable": row[4],
                    "permissions": int(row[5]),
                    "position": row[6],
                    "category_id": row[7],
                    "is_our_bot": bool(row[8]),
                }
                for row in cur.fetchall()
            ]
    return {"categories": categories, "roles": roles}


def _upsert_categories(cur: Any, categories: list[dict[str, Any]]) -> None:
	for c in categories:
		cur.execute(
			"""
			INSERT INTO role_categories (id, name, display_order, is_collapsed, permissions, is_restricted)
			VALUES (%s, %s, %s, %s, %s, %s)
			ON CONFLICT (id) DO UPDATE SET
				name = EXCLUDED.name,
				display_order = EXCLUDED.display_order,
				is_collapsed = EXCLUDED.is_collapsed,
				permissions = EXCLUDED.permissions,
				is_restricted = EXCLUDED.is_restricted
			""",
			(
				c["id"], c["name"], c.get("display_order", 0),
				c.get("is_collapsed", False), int(c.get("permissions", 0)),
				bool(c.get("is_restricted", False))
			),
		)


def _upsert_roles(cur: Any, roles: list[dict[str, Any]]) -> None:
	for r in roles:
		cur.execute(
			"""
			INSERT INTO role_manifests
			(role_id, name, color, hoist, mentionable, permissions, position, category_id, is_our_bot)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON CONFLICT (role_id) DO UPDATE SET
				name = EXCLUDED.name,
				color = EXCLUDED.color,
				hoist = EXCLUDED.hoist,
				mentionable = EXCLUDED.mentionable,
				permissions = EXCLUDED.permissions,
				position = EXCLUDED.position,
				category_id = EXCLUDED.category_id,
				is_our_bot = EXCLUDED.is_our_bot,
				updated_at = now()
			""",
			(
				r["role_id"], r["name"], r.get("color", "#000000"),
				r.get("hoist", False), r.get("mentionable", False),
				int(r.get("permissions", 0)), r["position"],
				r.get("category_id"), r.get("is_our_bot", False)
			),
		)


def _replace_manifest_rows(cur: Any, categories: list[dict[str, Any]], roles: list[dict[str, Any]]) -> None:
	"""マニフェストを送られた内容に置き換える。送られなかった行は削除し、それ以外は UPSERT する。"""
	cur.execute(
		"DELETE FROM role_manifests WHERE role_id <> ALL(%s)",
		([r["role_id"] for r in roles],),
	)
	cur.execute(
		"DELETE FROM role_categories WHERE id <> ALL(%s)",
		([c["id"] for c in categories],),
	)
	_upsert_categories(cur, categories)
	_upsert_roles(cur, roles)


def _snapshot_categories(cur: Any, ids: list[str] | None, *, lock: bool) -> dict[str, dict[str, Any]]:
	"""カテゴリの行を id -> 行 で読む。ids が None なら全件を読む。"""
	sql = "SELECT id, " + ", ".join(CATEGORY_AUDIT_FIELDS) + " FROM role_categories"
	params: tuple = ()
	if ids is not None:
		sql += " WHERE id = ANY(%s)"
		params = (ids,)
	if lock:
		sql += " FOR UPDATE"
	cur.execute(sql, params)
	return {row[0]: dict(zip(CATEGORY_AUDIT_FIELDS, row[1:])) for row in cur.fetchall()}


def _snapshot_roles(
	cur: Any,
	role_ids: list[str] | None,
	*,
	category_ids: list[str] | None = None,
	lock: bool,
) -> dict[str, dict[str, Any]]:
	"""ロールの行を role_id -> 行 で読む。role_ids が None なら全件を読む。

	category_ids を渡すと、そのカテゴリに属するロールも読む（カテゴリ削除の ON DELETE SET NULL で変わる行）。
	"""
	sql = "SELECT role_id, " + ", ".join(ROLE_AUDIT_FIELDS) + " FROM role_manifests"
	params: tuple = ()
	if role_ids is not None:
		sql += " WHERE role_id = ANY(%s) OR category_id = ANY(%s)"
		params = (role_ids, category_ids or [])
	if lock:
		sql += " FOR UPDATE"
	cur.execute(sql, params)
	return {row[0]: dict(zip(ROLE_AUDIT_FIELDS, row[1:])) for row in cur.fetchall()}


def _row_audit_logs(
	target_type: str,
	fields: tuple[str, ...],
	before_rows: dict[str, dict[str, Any]],
	after_rows: dict[str, dict[str, Any]],
) -> list[AuditLog]:
	"""変更前後の行を比べ、変わった行だけを監査ログにする（1対象1行）。"""
	logs: list[AuditLog] = []
	for target_id in sorted(set(before_rows) | set(after_rows)):
		before = before_rows.get(target_id)
		after = after_rows.get(target_id)
		diff = diff_fields(before, after, fields)
		if diff is None:
			continue
		action = ACTION_CREATE if before is None else ACTION_DELETE if after is None else ACTION_UPDATE
		logs.append(AuditLog(SYSTEM_DB, target_type, target_id, action, diff[0], diff[1]))
	return logs


def _assignment_audit_logs(changes: dict[str, tuple[list[str], list[str]]]) -> list[AuditLog]:
	logs: list[AuditLog] = []
	for role_id, (added, removed) in sorted(changes.items()):
		after = assignment_diff(added, removed)
		if after is not None:
			logs.append(AuditLog(SYSTEM_DB, TARGET_ROLE_ASSIGNMENT, role_id, ACTION_UPDATE, None, after))
	return logs


def save_manifest(categories: list[dict[str, Any]], roles: list[dict[str, Any]]) -> None:
	with _connect() as conn:
		with conn.cursor() as cur:
			_replace_manifest_rows(cur, categories, roles)
		conn.commit()


def replace_manifest(
	categories: list[dict[str, Any]],
	roles: list[dict[str, Any]],
	role_assignments: dict[str, list[str]],
	audit: AuditContext | None = None,
) -> None:
	"""PUT /api/v1/manifest の保存。マニフェストと割り当てを1つのトランザクションで置き換える。

	audit を渡すと、変更前の全行と比べて実際に追加・更新・削除された行だけを同じトランザクションで記録する。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			if audit is not None:
				before_categories = _snapshot_categories(cur, None, lock=True)
				before_roles = _snapshot_roles(cur, None, lock=True)
			_replace_manifest_rows(cur, categories, roles)
			changes = replace_role_assignments(cur, role_assignments)
			if audit is not None:
				insert_audit_logs(cur, audit, [
					*_row_audit_logs(TARGET_CATEGORY, CATEGORY_AUDIT_FIELDS, before_categories, _snapshot_categories(cur, None, lock=False)),
					*_row_audit_logs(TARGET_ROLE, ROLE_AUDIT_FIELDS, before_roles, _snapshot_roles(cur, None, lock=False)),
					*_assignment_audit_logs(changes),
				])
		conn.commit()


def update_role_id(old_id: str, new_id: str, audit: AuditContext | None = None) -> None:
	"""PushでDiscord側に作成されたロールの、DB上の仮IDを正規のDiscord IDに更新する。

	audit を渡すと、置き換えを1行（割り当ての置き換えも含む）で記録する。記録に失敗したら置き換えも失敗させる。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("UPDATE role_manifests SET role_id = %s WHERE role_id = %s", (new_id, old_id))
			renamed = cur.rowcount > 0
			cur.execute("UPDATE role_member_assignments SET role_id = %s WHERE role_id = %s", (new_id, old_id))
			renamed = renamed or cur.rowcount > 0
			if renamed:
				insert_audit_logs(cur, audit, [
					AuditLog(SYSTEM_DB, TARGET_ROLE, new_id, ACTION_RENAME_ID, {"role_id": old_id}, {"role_id": new_id}),
				])
		conn.commit()


def patch_manifest_db(
	upsert_categories: list[dict[str, Any]],
	delete_category_ids: list[str],
	upsert_roles: list[dict[str, Any]],
	delete_role_ids: list[str],
	upsert_role_assignments: dict[str, list[str]],
	audit: AuditContext | None = None,
) -> None:
	"""差分更新（PATCH）を使ってマニフェストを更新する

	audit を渡すと、変更のあった行だけを同じトランザクションで記録する。記録に失敗したら変更も失敗させる。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			if audit is not None:
				# 削除するカテゴリに属するロールは ON DELETE SET NULL で category_id が変わるため、読む範囲に含める
				category_ids = sorted({c["id"] for c in upsert_categories} | set(delete_category_ids))
				role_ids = sorted({r["role_id"] for r in upsert_roles} | set(delete_role_ids))
				before_categories = _snapshot_categories(cur, category_ids, lock=True)
				before_roles = _snapshot_roles(cur, role_ids, category_ids=list(delete_category_ids), lock=True)

			# 1. 削除処理
			if delete_role_ids:
				cur.execute("DELETE FROM role_manifests WHERE role_id = ANY(%s)", (delete_role_ids,))
			if delete_category_ids:
				cur.execute("DELETE FROM role_categories WHERE id = ANY(%s)", (delete_category_ids,))

			# 2. カテゴリのUPSERT
			_upsert_categories(cur, upsert_categories)

			# 3. ロールのUPSERT
			_upsert_roles(cur, upsert_roles)

			# 4. メンバー割り当ての適用（指定された role_id のみ。差分だけを更新する）
			changes = replace_role_assignments(cur, upsert_role_assignments)

			if audit is not None:
				after_categories = _snapshot_categories(cur, category_ids, lock=False)
				after_roles = _snapshot_roles(cur, sorted(set(role_ids) | set(before_roles)), lock=False)
				insert_audit_logs(cur, audit, [
					*_row_audit_logs(TARGET_CATEGORY, CATEGORY_AUDIT_FIELDS, before_categories, after_categories),
					*_row_audit_logs(TARGET_ROLE, ROLE_AUDIT_FIELDS, before_roles, after_roles),
					*_assignment_audit_logs(changes),
				])
		conn.commit()


class RoleNameConflictError(Exception):
	"""同じ名前のロールがすでにある。"""


def normalize_role_name(name: str) -> str:
	"""ロール名の重複判定に使う形にする（前後の空白と大文字・小文字の違いを無視する）。"""
	return name.strip().casefold()


def insert_member_created_role(role: dict[str, Any], audit: AuditContext | None = None) -> dict[str, Any]:
	"""member が作成したロールを、Discord で作成済みの実 ID でマニフェストに追加する。

	同名ロールの確認から追加までを、member によるロール作成同士で直列化する。
	position は既存ロールの最小値の1つ下（1 未満にはしない）にする。
	管理者画面の新規作成は Bot より下のロールだけから最小値を取るが、最下位のロールは通常 Bot より下にあるため、結果は同じになる。
	同じ名前のロールがあれば RoleNameConflictError を送出する。追加した行を返す。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("member-role-create",))
			existing = _snapshot_roles(cur, None, lock=True)
			name_key = normalize_role_name(role["name"])
			if any(normalize_role_name(str(r["name"])) == name_key for r in existing.values()):
				raise RoleNameConflictError(role["name"])
			positions = [int(r["position"]) for r in existing.values()]
			row = {**role, "position": max(1, min(positions) - 1) if positions else 1}
			_upsert_roles(cur, [row])
			insert_audit_logs(cur, audit, _row_audit_logs(
				TARGET_ROLE, ROLE_AUDIT_FIELDS, {}, _snapshot_roles(cur, [row["role_id"]], lock=False),
			))
		conn.commit()
	return row
