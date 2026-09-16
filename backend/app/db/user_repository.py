"""役割: ユーザーRBAC DBアクセス"""

from __future__ import annotations

import logging
from typing import Any

from app.db.repository import _connect

logger = logging.getLogger(__name__)


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
	'sub_user' は 'member' と同等として扱う。
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
								WHEN 'sub_user' THEN 2
								WHEN 'pre_member' THEN 3
								WHEN 'obog' THEN 4
					END LIMIT 1
					""",
					(discord_id,)
				)
				row = cur.fetchone()
				if row is not None:
					role = row[0]
					return "member" if role == "sub_user" else role
			except Exception:
				# user_memberships テーブル未作成などの環境では none を返す
				return "none"

	return "none"


def upsert_user(user_id: str, discord_id: str | None = None) -> dict[str, Any]:
	"""ユーザーを存在すれば更新して返し、存在しなければ新規作成する。
	サインイン時に user_memberships を参照し app_role を自動同期する。

	アカウント乗っ取り防止のため、既存ユーザーの user_id や discord_id の不正な上書きは行わない。
	"""
	if not user_id:
		raise ValueError("user_id is required")

	with _connect() as conn:
		with conn.cursor() as cur:
			# 1) user_id (Supabase UUID) 一致を確認
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
				current_discord_id = row[2]
				# 既に discord_id がバインドされている場合、不一致の別 discord_id での上書きは防止
				if current_discord_id and discord_id and current_discord_id != discord_id:
					logger.warning(
						"Discord ID conflict for user_id=%s: existing=%s, new=%s. Keeping existing.",
						user_id,
						current_discord_id,
						discord_id,
					)
					effective_discord_id = current_discord_id
				elif not current_discord_id and discord_id:
					# まだ discord_id が未登録だった場合のみ、安全にバインド
					# ただしその discord_id が既に他人に使われていないかチェック
					cur.execute(
						"SELECT id, user_id FROM users WHERE discord_id = %s AND user_id != %s",
						(discord_id, user_id),
					)
					conflict = cur.fetchone()
					if conflict:
						logger.error(
							"Security Violation: discord_id=%s already bound to user_id=%s, rejecting for user_id=%s",
							discord_id,
							conflict[1],
							user_id,
						)
						effective_discord_id = None
					else:
						cur.execute(
							"""
							UPDATE users
							SET discord_id = %s, updated_at = now()
							WHERE id = %s
							""",
							(discord_id, row[0]),
						)
						effective_discord_id = discord_id
				else:
					effective_discord_id = current_discord_id or discord_id

				resolved_role = _resolve_role_from_memberships(effective_discord_id)
				return {
					"id": row[0],
					"user_id": row[1],
					"discord_id": effective_discord_id,
					"app_role": resolved_role,
				}

			# 2) 新規ユーザー登録時: 既に同じ discord_id を持つ別ユーザーが存在しないか検証
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
					# 既に他人のアカウントがその Discord ID に紐づいているため、乗っ取り・上書きを禁止する
					logger.error(
						"Security Violation: Rejected user_id=%s attempting to claim existing discord_id=%s owned by user_id=%s",
						user_id,
						discord_id,
						by_discord[1],
					)
					# Discord ID なしで一般ユーザーとして作成
					discord_id = None

			resolved_role = _resolve_role_from_memberships(discord_id)
			cur.execute(
				"""
				INSERT INTO users (user_id, discord_id)
				VALUES (%s, %s)
				RETURNING id, user_id, discord_id
				""",
				(user_id, discord_id),
			)
			row = cur.fetchone()
			conn.commit()
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
	'sub_user' は 'member' として扱う。
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
						WHEN 'sub_user' THEN 2
						WHEN 'pre_member' THEN 3
						WHEN 'obog' THEN 4
				END LIMIT 1
				""",
				(discord_id,)
			)
			result = cur.fetchone()
			if not result:
				return "none"
			return "member" if result[0] == "sub_user" else result[0]


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
