"""役割: ユーザーRBAC DBアクセス"""

from __future__ import annotations

from typing import Any

from app.db.repository import _connect


def find_user_by_sub(user_id: str) -> dict[str, Any] | None:
	"""user_id (Supabase auth UUID) でユーザーを検索する。見つからない場合は None を返す。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, user_id, discord_id, app_role, created_at, updated_at
				FROM users
				WHERE user_id = %s
				""",
				(user_id,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"user_id": row[1],
				"discord_id": row[2],
				"app_role": row[3],
				"created_at": row[4],
				"updated_at": row[5],
			}


def upsert_user(user_id: str, discord_id: str | None = None) -> dict[str, Any]:
	"""ユーザーを存在すれば返し、存在しなければ app_role='none' で新規作成する。
	discord_id は初回登録時のみ設定し、以後は更新しない（上書きしない）。
	"""
	if not user_id:
		raise ValueError("user_id is required")

	with _connect() as conn:
		with conn.cursor() as cur:
			# 1) user_id 一致を最優先
			cur.execute(
				"""
				SELECT id, user_id, discord_id, app_role
				FROM users
				WHERE user_id = %s
				""",
				(user_id,),
			)
			row = cur.fetchone()
			if row is not None:
				# discord_id 未設定なら補完する
				if discord_id and not row[2]:
					cur.execute(
						"""
						UPDATE users
						SET discord_id = %s, updated_at = now()
						WHERE id = %s
						RETURNING id, user_id, discord_id, app_role
						""",
						(discord_id, row[0]),
					)
					updated = cur.fetchone()
					return {
						"id": updated[0],
						"user_id": updated[1],
						"discord_id": updated[2],
						"app_role": updated[3],
					}
				return {
					"id": row[0],
					"user_id": row[1],
					"discord_id": row[2],
					"app_role": row[3],
				}

			# 2) discord_id 一致があれば、既存ロールを保ったまま user_id を最新化
			if discord_id:
				cur.execute(
					"""
					SELECT id, user_id, discord_id, app_role
					FROM users
					WHERE discord_id = %s
					""",
					(discord_id,),
				)
				by_discord = cur.fetchone()
				if by_discord is not None:
					cur.execute(
						"""
						UPDATE users
						SET user_id = %s, updated_at = now()
						WHERE id = %s
						RETURNING id, user_id, discord_id, app_role
						""",
						(user_id, by_discord[0]),
					)
					updated = cur.fetchone()
					return {
						"id": updated[0],
						"user_id": updated[1],
						"discord_id": updated[2],
						"app_role": updated[3],
					}

			# 3) どちらにも一致しない場合だけ新規作成
			cur.execute(
				"""
				INSERT INTO users (user_id, discord_id, app_role)
				VALUES (%s, %s, 'none')
				RETURNING id, user_id, discord_id, app_role
				""",
				(user_id, discord_id),
			)
			row = cur.fetchone()
			return {
				"id": row[0],
				"user_id": row[1],
				"discord_id": row[2],
				"app_role": row[3],
			}


def get_user_role(user_id: str) -> str:
	"""ユーザーのapp_roleを返す。未登録の場合は 'none' を返す。"""
	user = find_user_by_sub(user_id)
	if user is None:
		return "none"
	return user["app_role"]


def update_user_role(user_id: str, role: str) -> None:
	"""ユーザーのapp_roleを更新する。"""
	valid_roles = {"member", "admin", "obog", "pre_member", "none"}
	if role not in valid_roles:
		raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE users SET app_role = %s, updated_at = now()
				WHERE user_id = %s
				""",
				(role, user_id),
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
