"""役割: PostgreSQLへの永続化処理"""

from __future__ import annotations

import os
from typing import Any

import psycopg2


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@postgres:5432/authwebapp")


def _connect():
	return psycopg2.connect(DATABASE_URL)


def init_db() -> None:
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				CREATE TABLE IF NOT EXISTS role_categories (
					id TEXT PRIMARY KEY,
					name TEXT NOT NULL,
					display_order INTEGER DEFAULT 0,
					is_collapsed BOOLEAN DEFAULT FALSE
				);
				"""
			)
			# カテゴリ権限カラムを追加（既存DBへの後方互換対応）
			cur.execute(
				"""
				ALTER TABLE role_categories
				ADD COLUMN IF NOT EXISTS permissions BIGINT DEFAULT 0;
				"""
			)
			cur.execute(
				"""
				CREATE TABLE IF NOT EXISTS role_manifests (
					role_id TEXT PRIMARY KEY,
					name TEXT NOT NULL,
					color TEXT DEFAULT '#000000',
					hoist BOOLEAN DEFAULT FALSE,
					mentionable BOOLEAN DEFAULT FALSE,
					permissions BIGINT DEFAULT 0,
					position INTEGER NOT NULL,
					category_id TEXT REFERENCES role_categories(id) ON DELETE SET NULL,
					is_managed_by_app BOOLEAN DEFAULT TRUE,
					updated_at TIMESTAMPTZ DEFAULT now()
				);
				"""
			)
			cur.execute(
				"""
				ALTER TABLE role_manifests
				ADD COLUMN IF NOT EXISTS is_our_bot BOOLEAN DEFAULT FALSE;
				"""
			)


def fetch_manifest() -> dict[str, list[dict[str, Any]]]:
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, name, display_order, is_collapsed, COALESCE(permissions, 0)
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
					INSERT INTO role_categories (id, name, display_order, is_collapsed, permissions)
					VALUES (%s, %s, %s, %s, %s)
					""",
					(
						c["id"],
						c["name"],
						c.get("display_order", 0),
						c.get("is_collapsed", False),
						int(c.get("permissions", 0)),
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
	return len(roles)


def update_role_id(old_id: str, new_id: str) -> None:
	"""PushでDiscord側に作成されたロールの、DB上の仮IDを正規のDiscord IDに更新する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("UPDATE role_manifests SET role_id = %s WHERE role_id = %s", (new_id, old_id))


