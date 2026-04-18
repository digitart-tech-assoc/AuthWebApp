"""役割: ユーザーRBAC DBアクセス"""

from __future__ import annotations

from typing import Any

from app.db.repository import _connect


def find_user_by_sub(user_id: str) -> dict[str, Any] | None:
	"""user_id (Supabase auth UUID) でユーザーを検索する。見つからない場合は None を返す。
	
	注意: app_role は計算値となるため、別途 get_user_role() で取得してください。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, user_id, discord_id, created_at, updated_at
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
				"created_at": row[3],
				"updated_at": row[4],
			}


def _resolve_role_from_memberships(discord_id: str | None) -> str:
	"""user_memberships から app_role を解決する。
	優先順位: admin > member > pre_member > obog > none
	"""
	if not discord_id:
		return "none"

	with _connect() as conn:
		with conn.cursor() as cur:
			try:
				cur.execute(
					"""
					SELECT membership_type FROM user_memberships 
					WHERE discord_id = %s 
					ORDER BY CASE membership_type 
						WHEN 'admin' THEN 1
						WHEN 'member' THEN 2
						WHEN 'pre_member' THEN 3
						WHEN 'obog' THEN 4
					END LIMIT 1
					""",
					(discord_id,)
				)
				row = cur.fetchone()
				if row is not None:
					return row[0]
			except Exception:
				# user_memberships テーブル未作成などの環境では none を返す
				return "none"

	return "none"


def upsert_user(user_id: str, discord_id: str | None = None) -> dict[str, Any]:
	"""ユーザーを存在すれば更新して返し、存在しなければ新規作成する。
	サインイン時に user_memberships を参照し app_role を自動同期する。
	
	注意: 戻り値に含まれた app_role は参考値です。実際の権限判定には必ず get_user_role() を使用してください。
	"""
	if not user_id:
		raise ValueError("user_id is required")

	with _connect() as conn:
		with conn.cursor() as cur:
			resolved_role = _resolve_role_from_memberships(discord_id)
			# 1) user_id 一致を最優先
			cur.execute(
				"""
				SELECT id, user_id, discord_id
				FROM users
				WHERE user_id = %s
				""",
				(user_id,),
			)
			row = cur.fetchone()
			if row is not None:
				next_discord_id = row[2] or discord_id
				next_role = _resolve_role_from_memberships(next_discord_id)
				# discord_id/app_role のどちらかが変わる場合のみ更新
				if (discord_id and not row[2]) or (next_role != resolved_role):
					cur.execute(
						"""
						UPDATE users
						SET discord_id = %s, updated_at = now()
						WHERE id = %s
						RETURNING id, user_id, discord_id
						""",
						(next_discord_id, row[0]),
					)
					updated = cur.fetchone()
					return {
						"id": updated[0],
						"user_id": updated[1],
						"discord_id": updated[2],
						"app_role": next_role,
					}
				return {
					"id": row[0],
					"user_id": row[1],
					"discord_id": next_discord_id,
					"app_role": next_role,
				}

			# 2) discord_id 一致があれば、既存ロールを保ったまま user_id を最新化
			if discord_id:
				cur.execute(
					"""
					SELECT id, user_id, discord_id
					FROM users
					WHERE discord_id = %s
					""",
					(discord_id,),
				)
				by_discord = cur.fetchone()
				if by_discord is not None:
					next_role = _resolve_role_from_memberships(discord_id)
					cur.execute(
						"""
						UPDATE users
						SET user_id = %s, updated_at = now()
						WHERE id = %s
						RETURNING id, user_id, discord_id
						""",
						(user_id, by_discord[0]),
					)
					updated = cur.fetchone()
					return {
						"id": updated[0],
						"user_id": updated[1],
						"discord_id": updated[2],
						"app_role": next_role,
					}

			# 3) どちらにも一致しない場合だけ新規作成
			cur.execute(
				"""
				INSERT INTO users (user_id, discord_id)
				VALUES (%s, %s)
				RETURNING id, user_id, discord_id
				""",
				(user_id, discord_id),
			)
			row = cur.fetchone()
			return {
				"id": row[0],
				"user_id": row[1],
				"discord_id": row[2],
				"app_role": resolved_role,
			}


def get_user_role(user_id: str) -> str:
	"""ユーザーの app_role を返す。未登録の場合は 'none' を返す。
	
	app_role は user_memberships から計算される値です。
	優先順位: admin > member > pre_member > obog > none
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# user_id から discord_id を取得
			cur.execute("SELECT discord_id FROM users WHERE user_id = %s", (user_id,))
			row = cur.fetchone()
			if not row or not row[0]:
				return "none"
			
			discord_id = row[0]
			
			# user_memberships から membership_type を取得
			cur.execute(
				"""
				SELECT membership_type FROM user_memberships 
				WHERE discord_id = %s 
				ORDER BY CASE membership_type 
					WHEN 'admin' THEN 1
					WHEN 'member' THEN 2
					WHEN 'pre_member' THEN 3
					WHEN 'obog' THEN 4
				END LIMIT 1
				""",
				(discord_id,)
			)
			result = cur.fetchone()
			return result[0] if result else "none"


def update_user_role(user_id: str, role: str) -> None:
	"""【DEPRECATED】ユーザーのapp_roleを更新する。
	
	users.app_role カラムは削除予定のため、この関数は使用しないでください。
	app_role は user_memberships から自動計算されます。
	"""
	raise NotImplementedError(
		"update_user_role() is deprecated. app_role is now calculated from user_memberships. "
		"Use repository functions to manage user memberships instead."
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

def get_guild_member_info(discord_id: str) -> dict[str, Any] | None:
	"""discord_id から current profile info を取得する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT display_name, avatar, username FROM guild_members
				WHERE user_id = %s
				""",
				(discord_id,)
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"display_name": row[0] or row[2],
				"avatar": row[1]
			}
