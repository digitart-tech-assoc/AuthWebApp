"""役割: ロールマニフェストおよびロールカテゴリに関する永続化処理"""

from __future__ import annotations

from typing import Any

from app.db.connection import _connect


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


def save_manifest(categories: list[dict[str, Any]], roles: list[dict[str, Any]]) -> None:
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("DELETE FROM role_manifests")
			cur.execute("DELETE FROM role_categories")

			for c in categories:
				cur.execute(
					"""
					INSERT INTO role_categories (id, name, display_order, is_collapsed, permissions, is_restricted)
					VALUES (%s, %s, %s, %s, %s, %s)
					""",
					(
						c["id"],
						c["name"],
						c.get("display_order", 0),
						c.get("is_collapsed", False),
						int(c.get("permissions", 0)),
						bool(c.get("is_restricted", False)),
					),
				)

			for r in roles:
				cur.execute(
					"""
					INSERT INTO role_manifests
					(role_id, name, color, hoist, mentionable, permissions, position, category_id, is_our_bot)
					VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
					""",
					(
						r["role_id"],
						r["name"],
						r.get("color", "#000000"),
						r.get("hoist", False),
						r.get("mentionable", False),
						int(r.get("permissions", 0)),
						r["position"],
						r.get("category_id"),
						r.get("is_our_bot", False),
					),
				)
		conn.commit()


def replace_roles_from_discord(roles: list[dict[str, Any]]) -> int:
	with _connect() as conn:
		with conn.cursor() as cur:
			existing_ids = tuple(role["role_id"] for role in roles)
			if existing_ids:
				cur.execute("DELETE FROM role_manifests WHERE role_id NOT IN %s", (existing_ids,))
			else:
				cur.execute("DELETE FROM role_manifests")

			for role in roles:
				cur.execute(
					"""
					INSERT INTO role_manifests
					(role_id, name, color, hoist, mentionable, permissions, position, is_our_bot)
					VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
					ON CONFLICT (role_id) DO UPDATE SET
						name = EXCLUDED.name,
						color = EXCLUDED.color,
						hoist = EXCLUDED.hoist,
						mentionable = EXCLUDED.mentionable,
						permissions = EXCLUDED.permissions,
						position = EXCLUDED.position,
						is_our_bot = EXCLUDED.is_our_bot
					""",
					(
						role["role_id"],
						role["name"],
						role["color"],
						role["hoist"],
						role["mentionable"],
						role["permissions"],
						role["position"],
						role.get("is_our_bot", False),
					),
				)
		conn.commit()
	return len(roles)


def update_role_id(old_id: str, new_id: str) -> None:
	"""PushでDiscord側に作成されたロールの、DB上の仮IDを正規のDiscord IDに更新する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("UPDATE role_manifests SET role_id = %s WHERE role_id = %s", (new_id, old_id))
			cur.execute("UPDATE role_member_assignments SET role_id = %s WHERE role_id = %s", (new_id, old_id))
		conn.commit()


def patch_manifest_db(
	upsert_categories: list[dict[str, Any]],
	delete_category_ids: list[str],
	upsert_roles: list[dict[str, Any]],
	delete_role_ids: list[str],
	upsert_role_assignments: dict[str, list[str]]
) -> None:
	"""差分更新（PATCH）を使ってマニフェストを更新する"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# 1. 削除処理
			if delete_role_ids:
				cur.execute("DELETE FROM role_manifests WHERE role_id = ANY(%s)", (delete_role_ids,))
			if delete_category_ids:
				cur.execute("DELETE FROM role_categories WHERE id = ANY(%s)", (delete_category_ids,))

			# 2. カテゴリのUPSERT
			for c in upsert_categories:
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

			# 3. ロールのUPSERT
			for r in upsert_roles:
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

			# 4. メンバー割り当ての適用（指定された role_id のみ）
			for role_id, user_ids in upsert_role_assignments.items():
				cur.execute("DELETE FROM role_member_assignments WHERE role_id = %s", (role_id,))
				for user_id in user_ids:
					cur.execute(
						"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
						(role_id, user_id),
					)
		conn.commit()
