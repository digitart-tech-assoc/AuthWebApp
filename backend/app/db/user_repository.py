"""役割: ユーザーRBAC DBアクセス"""

from __future__ import annotations

from typing import Any

from app.db.repository import _connect


def find_user_by_sub(keycloak_sub: str) -> dict[str, Any] | None:
	"""keycloak_sub でユーザーを検索する。見つからない場合は None を返す。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, keycloak_sub, discord_id, app_role, created_at, updated_at
				FROM users
				WHERE keycloak_sub = %s
				""",
				(keycloak_sub,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"keycloak_sub": row[1],
				"discord_id": row[2],
				"app_role": row[3],
				"created_at": row[4],
				"updated_at": row[5],
			}


def upsert_user(keycloak_sub: str, discord_id: str | None = None) -> dict[str, Any]:
	"""ユーザーを存在すれば返し、存在しなければ app_role='none' で新規作成する。
	discord_id は初回登録時のみ設定し、以後は更新しない（上書きしない）。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO users (keycloak_sub, discord_id, app_role)
				VALUES (%s, %s, 'none')
				ON CONFLICT (keycloak_sub) DO UPDATE
					SET discord_id = COALESCE(users.discord_id, EXCLUDED.discord_id),
					    updated_at = now()
				RETURNING id, keycloak_sub, discord_id, app_role
				""",
				(keycloak_sub, discord_id),
			)
			row = cur.fetchone()
			return {
				"id": row[0],
				"keycloak_sub": row[1],
				"discord_id": row[2],
				"app_role": row[3],
			}


def get_user_role(keycloak_sub: str) -> str:
	"""ユーザーのapp_roleを返す。未登録の場合は 'none' を返す。"""
	user = find_user_by_sub(keycloak_sub)
	if user is None:
		return "none"
	return user["app_role"]


def update_user_role(keycloak_sub: str, role: str) -> None:
	"""ユーザーのapp_roleを更新する。"""
	valid_roles = {"member", "admin", "obog", "pre_member", "none"}
	if role not in valid_roles:
		raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE users SET app_role = %s, updated_at = now()
				WHERE keycloak_sub = %s
				""",
				(role, keycloak_sub),
			)


def is_paid_invitation(discord_id: str) -> bool:
	"""discord_id が入会費支払い済みリストに存在するか確認する。
	期限が設定されている場合は現在より未来のもののみ有効。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT 1 FROM paid_invitations
				WHERE discord_id = %s
				  AND (expires_at IS NULL OR expires_at > now())
				""",
				(discord_id,),
			)
			return cur.fetchone() is not None
