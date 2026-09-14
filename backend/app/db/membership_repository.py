"""役割: ユーザーメンバーシップに関する永続化処理"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import MEMBERSHIP_PRIORITY_SQL, MembershipType
from app.db.connection import _connect, _log_db_access

logger = logging.getLogger(__name__)


def is_prospective_form_open() -> bool:
	"""入学見込み仮入会フォームが受け付け可能な期間か判定（毎年2月1日～4月5日、日本時間）
	
	Returns:
		True: 受け付け可能期間内
		False: 受け付け不可期間
	"""
	# 日本時間（JST）で現在日付を取得
	jst_tz = timezone(timedelta(hours=9))
	now = datetime.now(jst_tz)
	month = now.month
	day = now.day
	
	# 2月1日～4月5日の範囲判定
	if month == 2 and day >= 1:
		return True
	elif month == 3:
		return True
	elif month == 4 and day <= 5:
		return True
	else:
		return False


def sync_member_lists(
	member_role_ids: list[str],
	obog_role_ids: list[str],
	admin_role_ids: list[str],
	pre_member_role_id: str | None,
	members: dict[str, list[dict[str, Any]]],
	sub_user_role_ids: list[str] | None = None,
) -> dict[str, Any]:
	"""
	Discord ロール情報から user_memberships を同期。
	user_memberships テーブルの新仕様に対応。
	
	Parameters:
	- member_role_ids: member ロール ID のリスト
	- obog_role_ids: OBOG ロール ID のリスト
	- admin_role_ids: admin ロール ID のリスト
	- pre_member_role_id: pre-member ロール ID（持っている場合）
	- members: role_id -> [members] のマッピング（fetch_guild_members_with_role から取得）
	
	Returns:
	- {
		'member_list': [list of user_memberships records],
		'admin_list': [list of user_memberships records],
		'pre_member_list': [list of user_memberships records],
		'obog_list': [list of user_memberships records],
	}
	"""
	# Validation: すべての role_id がメンバーデータを持つことを確認
	expected_role_ids = set(member_role_ids + obog_role_ids + admin_role_ids)
	if pre_member_role_id:
		expected_role_ids.add(pre_member_role_id)
	# sub_user_role_ids が指定されていれば期待値に含める
	if sub_user_role_ids:
		expected_role_ids.update(sub_user_role_ids)
	
	provided_role_ids = set(members.keys())
	
	# 欠落している role_id をチェック
	missing_role_ids = expected_role_ids - provided_role_ids
	if missing_role_ids:
		error_msg = f"Missing members data for role_ids: {missing_role_ids}. Aborting sync to prevent data loss."
		logger.error(error_msg)
		raise ValueError(error_msg)
	
	with _connect() as conn:
		with conn.cursor() as cur:
			# 既存データをバックアップ（念のため）
			cur.execute("SELECT COUNT(*) FROM user_memberships")
			old_count = cur.fetchone()[0]
			logger.info(f"Backing up existing user_memberships: {old_count} records")
			
			# 既存データをクリア（全置換方式）
			cur.execute("DELETE FROM user_memberships")
			logger.info("Cleared user_memberships table")
			
			result = {
				'member_list': [],
				'sub_user_list': [],
				'admin_list': [],
				'pre_member_list': [],
				'obog_list': []
			}
			
			# ユーティリティ関数: タプルを辞書に変換（タイムスタンプをISO形式に）
			def row_to_dict(row, description):
				result = {}
				for desc, val in zip(description, row):
					col_name = desc[0]
					# タイムスタンプ型はISO形式の文字列に変換
					if col_name in ['assigned_at', 'created_at'] and val is not None:
						result[col_name] = val.isoformat()
					else:
						result[col_name] = val
				return result
			
			def _insert_membership_batch(role_ids, m_type, r_list):
				discord_ids = set()
				for role_id in role_ids:
					for member in members.get(role_id, []):
						discord_ids.add(member["user_id"])
				if not discord_ids:
					return
				logger.info(f"Syncing {len(discord_ids)} members with membership_type='{m_type}'")
				for discord_id in discord_ids:
					cur.execute(
						"""
						INSERT INTO user_memberships 
						(discord_id, membership_type, assigned_at, created_at)
						VALUES (%s, %s, now(), now())
						ON CONFLICT (discord_id, membership_type) DO NOTHING
						RETURNING *
						""",
						(discord_id, m_type)
					)
					row = cur.fetchone()
					if row:
						r_list.append(row_to_dict(row, cur.description))

			sync_targets = [
				(member_role_ids, MembershipType.MEMBER, result['member_list']),
				(sub_user_role_ids or [], MembershipType.SUB_USER, result['sub_user_list']),
				(obog_role_ids, MembershipType.OBOG, result['obog_list']),
				(admin_role_ids, MembershipType.ADMIN, result['admin_list']),
				([pre_member_role_id] if pre_member_role_id else [], MembershipType.PRE_MEMBER, result['pre_member_list']),
			]
			for r_ids, m_type, r_list in sync_targets:
				_insert_membership_batch(r_ids, m_type, r_list)
			
			conn.commit()

			# 完了ログ
			total_synced = sum(len(v) for v in result.values())
			logger.info(
				f"sync_member_lists completed: {total_synced} total records synced "
				f"(member={len(result['member_list'])}, sub_user={len(result['sub_user_list'])}, "
				f"admin={len(result['admin_list'])}, pre_member={len(result['pre_member_list'])}, obog={len(result['obog_list'])})"
			)

			return result


def get_member_lists() -> dict[str, list[dict[str, Any]]]:
	"""user_memberships から membership_type 別にリストを取得."""
	with _connect() as conn:
		with conn.cursor() as cur:
			result = {}
			
			# membership_type ごとにクエリ
			for mem_type in ['member','sub_user','admin','pre_member','obog']:
				cur.execute(
					"""
					SELECT discord_id, assigned_by, assigned_at
					FROM user_memberships
					WHERE membership_type = %s
					ORDER BY assigned_at DESC
					""",
					(mem_type,)
				)
				result[f'{mem_type}_list'] = [
					{
						'discord_id': row[0],
						'assigned_by': row[1],
						'assigned_at': row[2].isoformat() if row[2] else None
					}
					for row in cur.fetchall()
				]
			
			return result


# ==========================================
# user_memberships 用ユーティリティ関数
# ==========================================

def get_user_membership_type(discord_id: str) -> str:
	"""user_memberships から membership_type を取得。
	
	優先順位: admin > member/sub_user > pre_member > obog > none
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				f"""
				SELECT membership_type FROM user_memberships 
				WHERE discord_id = %s 
				{MEMBERSHIP_PRIORITY_SQL}
				LIMIT 1
				""",
				(discord_id,)
			)
			row = cur.fetchone()
			return row[0] if row else 'none'


def has_membership(discord_id: str, membership_type: str | tuple[str, ...] | list[str]) -> bool:
	"""指定された discord_id が指定の membership_type を所持しているか判定。"""
	types = [membership_type] if isinstance(membership_type, str) else list(membership_type)
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"SELECT 1 FROM user_memberships WHERE discord_id = %s AND membership_type = ANY(%s) LIMIT 1",
				(discord_id, types)
			)
			return cur.fetchone() is not None


def is_member(discord_id: str) -> bool:
	"""user_memberships で member (または sub_user) か確認."""
	return has_membership(discord_id, (MembershipType.MEMBER, MembershipType.SUB_USER))


def is_admin(discord_id: str) -> bool:
	"""user_memberships で admin か確認."""
	return has_membership(discord_id, MembershipType.ADMIN)


def is_pre_member(discord_id: str) -> bool:
	"""user_memberships で pre_member か確認."""
	return has_membership(discord_id, MembershipType.PRE_MEMBER)


def is_obog(discord_id: str) -> bool:
	"""user_memberships で obog か確認."""
	return has_membership(discord_id, MembershipType.OBOG)


def add_to_user_membership(discord_id: str, membership_type: str) -> None:
	"""user_memberships にメンバーシップを追加。"""
	if membership_type not in MembershipType.ALL:
		raise ValueError(f"Invalid membership_type: {membership_type}")
	
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO user_memberships (discord_id, membership_type, assigned_at, created_at)
				VALUES (%s, %s, now(), now())
				ON CONFLICT (discord_id, membership_type) DO NOTHING
				""",
				(discord_id, membership_type)
			)
			conn.commit()


def remove_from_user_membership(discord_id: str, membership_type: str) -> None:
	"""user_memberships からメンバーシップを削除。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"DELETE FROM user_memberships WHERE discord_id = %s AND membership_type = %s",
				(discord_id, membership_type)
			)
			conn.commit()


def get_pre_member_list_v2() -> list[str]:
	"""user_memberships から pre_member の discord_id リストを取得。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"SELECT discord_id FROM user_memberships WHERE membership_type = 'pre_member' ORDER BY assigned_at DESC"
			)
			return [row[0] for row in cur.fetchall()]


def get_membership_count(membership_type: str | tuple[str, ...] | list[str]) -> int:
	"""指定された membership_type の件数を取得。"""
	types = [membership_type] if isinstance(membership_type, str) else list(membership_type)
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"SELECT COUNT(*) FROM user_memberships WHERE membership_type = ANY(%s)",
				(types,)
			)
			row = cur.fetchone()
			return row[0] if row else 0


def get_member_user_count() -> int:
	"""user_memberships の member 件数。"""
	return get_membership_count(MembershipType.MEMBER)


def get_admin_user_count() -> int:
	"""user_memberships の admin 件数。"""
	return get_membership_count(MembershipType.ADMIN)


def get_pre_member_user_count() -> int:
	"""user_memberships の pre_member 件数。"""
	return get_membership_count(MembershipType.PRE_MEMBER)


def register_pre_member(discord_id: str, source: str | None = None) -> dict[str, Any]:
	"""新しい参加者を user_memberships (pre_member) に登録.
	
	Args:
		discord_id: Discord user ID
		source: 登録ソース (デフォルト: None)
		
	Returns:
		{"discord_id": "...", "created": True/False}
	"""
	pre_member_role_id = os.getenv("PRE_MEMBER_ROLE_ID", "").strip()
	with _connect() as conn:
		with conn.cursor() as cur:
			# Check if already registered as pre_member
			cur.execute(
				"""
				SELECT assigned_at, created_at
				FROM user_memberships
				WHERE discord_id = %s AND membership_type = 'pre_member'
				""",
				(discord_id,)
			)
			existing = cur.fetchone()
			created = False
			assigned_at = None
			created_at = None

			if existing is not None:
				assigned_at, created_at = existing
			else:
				# Insert into user_memberships
				cur.execute(
					"""
					INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
					VALUES (%s, 'pre_member', %s, now(), now())
					ON CONFLICT (discord_id, membership_type) DO NOTHING
					RETURNING created_at, assigned_at
				""",
					(discord_id, source)
				)

				result = cur.fetchone()
				if result is None:
					conn.commit()
					return {"discord_id": discord_id, "created": False, "message": "Failed to insert"}

				created = True
				created_at, assigned_at = result[0], result[1]

			role_assignment_created = False
			if pre_member_role_id:
				cur.execute(
					"""
					INSERT INTO role_member_assignments (role_id, user_id)
					VALUES (%s, %s)
					ON CONFLICT DO NOTHING
					""",
					(pre_member_role_id, discord_id),
				)
				role_assignment_created = cur.rowcount > 0
			else:
				# Keep the registration itself working, but make the missing configuration visible in logs.
				logger.warning("PRE_MEMBER_ROLE_ID is not configured; skipping role_member_assignments insert")
			conn.commit()

			return {
				"discord_id": discord_id,
				"created": created,
				"message": "Already in pre_member" if not created and existing is not None else None,
				"assigned_at": assigned_at.isoformat() if assigned_at else created_at.isoformat() if created_at else None,
				"assigned_by": source,
				"pre_member_role_id": pre_member_role_id or None,
				"role_assignment_created": role_assignment_created,
			}


def expiry_from_assigned_at(assigned_at):
	"""Calculate expiry (UTC) from an assigned_at datetime using fiscal-year logic (4月開始).

	Returns a timezone-aware UTC datetime corresponding to that fiscal year's April 30 23:59:59 JST.
	"""
	if assigned_at is None:
		return None
	jst = ZoneInfo("Asia/Tokyo")
	# Ensure assigned_at is timezone-aware (assume UTC if naive)
	if getattr(assigned_at, "tzinfo", None) is None:
		assigned_at = assigned_at.replace(tzinfo=timezone.utc)
	assigned_jst = assigned_at.astimezone(jst)
	fiscal = assigned_jst.year if assigned_jst.month >= 4 else assigned_jst.year - 1
	expiry_jst = datetime(fiscal + 1, 4, 30, 23, 59, 59, tzinfo=jst)
	return expiry_jst.astimezone(timezone.utc)


def cleanup_expired_prospective_members() -> dict[str, int]:
	"""Remove expired prospective pre-members (assigned_by = 'P').

	Returns a dict with counts: {"removed": n}
	"""
	removed = 0
	now = datetime.now(timezone.utc)
	with _connect() as conn:
		with conn.cursor() as cur:
			# Get pre_member entries from user_memberships (assigned_by = 'P')
			cur.execute(
				"SELECT discord_id, assigned_at FROM user_memberships WHERE membership_type = 'pre_member' AND assigned_by = %s",
				("P",)
			)
			rows = cur.fetchall()
			to_remove = []
			for row in rows:
				discord_id, assigned_at = row[0], row[1]
				expiry = expiry_from_assigned_at(assigned_at)
				if expiry is not None and expiry < now:
					to_remove.append((discord_id, expiry))

			# Ensure removal log table exists (best-effort)
			try:
				cur.execute(
					"""
					CREATE TABLE IF NOT EXISTS pre_member_removal_log (
						id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
						discord_id TEXT NOT NULL,
						source_flow TEXT,
						expired_at TIMESTAMPTZ,
						removed_at TIMESTAMPTZ DEFAULT now(),
						reason TEXT,
						created_at TIMESTAMPTZ DEFAULT now()
					);
				"""
			)
			except Exception:
				# If creation fails, continue without log
				pass

			for discord_id, expiry in to_remove:
				cur.execute("DELETE FROM user_memberships WHERE discord_id = %s AND membership_type = 'pre_member'", (discord_id,))
				try:
					cur.execute(
						"INSERT INTO pre_member_removal_log (discord_id, source_flow, expired_at, reason) VALUES (%s, %s, %s, %s)",
						(discord_id, "P", expiry, "Expired prospective member"),
					)
				except Exception:
					# swallow logging errors
					pass
				removed += 1

		conn.commit()

	return {"removed": removed}


def get_pre_member_list_with_users(search: str | None = None) -> list[dict[str, Any]]:
	"""Pre-member list を user_memberships から取得。
	paid_invitations に含まれているかどうかも判定。
	
	Args:
		search: discord_id で検索（部分一致）
		
	Returns:
		[{"discord_id": "...", "assigned_at": "...", "is_paid": bool, ...}, ...]
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			if search:
				# discord_id で部分検索
				cur.execute(
					"""
					SELECT p.discord_id, p.assigned_at, 
						   CASE WHEN pi.discord_id IS NOT NULL THEN true ELSE false END as is_paid
					FROM user_memberships p
					LEFT JOIN paid_invitations pi ON p.discord_id = pi.discord_id
					WHERE p.membership_type = 'pre_member' AND p.discord_id ILIKE %s
					ORDER BY p.assigned_at DESC
				""",
					(f"%{search}%",)
			)
			else:
				cur.execute(
					"""
					SELECT p.discord_id, p.assigned_at, 
						   CASE WHEN pi.discord_id IS NOT NULL THEN true ELSE false END as is_paid
					FROM user_memberships p
					LEFT JOIN paid_invitations pi ON p.discord_id = pi.discord_id
					WHERE p.membership_type = 'pre_member'
					"""
				)
			
			results = []
			for row in cur.fetchall():
				results.append({
					"discord_id": row[0],
					"assigned_at": row[1].isoformat() if row[1] else None,
					"is_paid": row[2],
					"discord_username": None,  # Will be populated by API with Discord API call
				})
			return results


def add_to_member_list(
	discord_id: str,
	assigned_by: str,
	note: str | None = None,
) -> dict[str, Any]:
	"""pre_member を member に昇格（user_memberships で管理）。
	同時に paid_invitations にも登録する。
	
	Args:
		discord_id: Discord user ID
		assigned_by: admin's discord_id or user_id
		note: Optional note for paid_invitations
		
	Returns:
		{"discord_id": "...", "added_to_member_list": True/False}
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# Check if already member in user_memberships
			cur.execute(
				"SELECT 1 FROM user_memberships WHERE discord_id = %s AND membership_type = 'member'",
				(discord_id,)
			)
			if cur.fetchone() is not None:
				return {"discord_id": discord_id, "added_to_member_list": False, "message": "Already member"}
			
			# Add to user_memberships as member
			cur.execute(
				"""
				INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
				VALUES (%s, 'member', %s, now(), now())
				ON CONFLICT (discord_id, membership_type) DO NOTHING
				RETURNING created_at, assigned_at
				""",
				(discord_id, assigned_by)
			)
			result = cur.fetchone()
			
			# Also register in paid_invitations if not already there
			cur.execute(
				"SELECT discord_id FROM paid_invitations WHERE discord_id = %s AND status = 'completed'",
				(discord_id,)
			)
			if cur.fetchone() is None:
				cur.execute(
					"""
					INSERT INTO paid_invitations (discord_id, note, status, assigned_by, assigned_at)
					VALUES (%s, %s, 'completed', %s, now())
					""",
					(discord_id, note, assigned_by)
				)
			
			# Remove from pre_member membership if present
			cur.execute(
				"DELETE FROM user_memberships WHERE discord_id = %s AND membership_type = 'pre_member'",
				(discord_id,)
			)
			
			conn.commit()
			
			return {
				"discord_id": discord_id,
				"added_to_member_list": True,
				"created_at": result[0].isoformat() if result and result[0] else None
			}


def register_paid_invitation(
	discord_id: str,
	note: str | None = None,
	assigned_by: str | None = None,
) -> dict[str, Any]:
	"""入会費支払い済みユーザーを paid_invitations に登録。
	
	Args:
		discord_id: Discord user ID
		note: Payment method or note
		assigned_by: admin's discord_id or user_id
		
	Returns:
		{"discord_id": "...", "created": True/False}
	"""
	# assigned_by が None の場合はデフォルト値を使用
	final_assigned_by = assigned_by or "unknown"
	_log_db_access("register_paid_invitation", {"discord_id": discord_id, "note": note, "assigned_by": final_assigned_by})

	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO paid_invitations (discord_id, note, assigned_by)
				VALUES (%s, %s, %s)
				ON CONFLICT (discord_id) DO UPDATE SET note = EXCLUDED.note, assigned_by = EXCLUDED.assigned_by, assigned_at = now()
				RETURNING id, created_at, assigned_at
				""",
				(discord_id, note, final_assigned_by)
			)
			result = cur.fetchone()
			conn.commit()
			
			return {
				"discord_id": discord_id,
				"created": True,
				"assigned_at": result[2].isoformat() if result[2] else None,
				"assigned_by": final_assigned_by
			}
