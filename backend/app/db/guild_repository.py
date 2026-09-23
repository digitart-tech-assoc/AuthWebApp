"""役割: ギルドメンバーおよびロール割り当てに関する永続化処理"""

from __future__ import annotations

import logging
from typing import Any

from app.db.connection import _connect

logger = logging.getLogger(__name__)


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


def save_role_assignments(assignments: dict[str, list[str]]) -> None:
	"""
	role_id -> [user_id, ...] のマッピングでロール割り当てを全置き換え保存。
	assignments に含まれる role_id の割り当てのみ上書き。含まれない role_id は触らない。
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			total_inserted = 0
			total_roles = len(assignments)
			
			for role_id, user_ids in assignments.items():
				try:
					# 既存の割り当てを削除
					cur.execute("DELETE FROM role_member_assignments WHERE role_id = %s", (role_id,))
					deleted = cur.rowcount
					
					# 新しい割り当てを挿入
					inserted = 0
					for user_id in user_ids:
						cur.execute(
							"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
							(role_id, user_id),
						)
						inserted += cur.rowcount
					
					total_inserted += inserted
					logger.debug(f"save_role_assignments: role_id={role_id} deleted={deleted} inserted={inserted}")
				except Exception as e:
					logger.error(f"save_role_assignments error for role_id={role_id}: {e}")
					raise
			
		conn.commit()
		logger.info(f"save_role_assignments completed: {total_roles} roles, {total_inserted} total assignments")


def add_user_to_role(user_id: str, role_id: str) -> None:
	"""特定ユーザーをロールに追加する（重複チェック付き）。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
				(role_id, user_id),
			)
			conn.commit()


def remove_user_from_role(user_id: str, role_id: str) -> None:
	"""特定ユーザーをロールから削除する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
				(role_id, user_id),
			)
			conn.commit()


def batch_update_user_roles(user_id: str, roles_to_add: list[str], roles_to_remove: list[str]) -> None:
	"""1ユーザーのロール割り当てを一括で追加/削除する（1トランザクション）。

	Args:
		user_id:        対象ユーザーの Discord ID
		roles_to_add:   追加するロール ID リスト
		roles_to_remove: 削除するロール ID リスト
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# 同一ユーザーのDB更新を同時に行う処理間で直列化する。
			cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"self-role:{user_id}",))
			for role_id in roles_to_remove:
				cur.execute(
					"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
					(role_id, user_id),
				)
			for role_id in roles_to_add:
				cur.execute(
					"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
					(role_id, user_id),
				)
		conn.commit()
		logger.info(
			"batch_update_user_roles: user_id=%s added=%s removed=%s",
			user_id,
			roles_to_add,
			roles_to_remove,
		)


def clear_all_role_assignments() -> None:
	"""role_member_assignments テーブルの全行を削除する（Discordから完全再取得する際に使用）。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute("DELETE FROM role_member_assignments")
		conn.commit()


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
