"""役割: 学生登録および学生用OTPに関する永続化処理"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.db.connection import _connect, _log_db_access

logger = logging.getLogger(__name__)


def is_paid_invitation(discord_id: str) -> bool:
	"""Discord IDが支払済リストにあるか確認"""
	try:
		with _connect() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"SELECT 1 FROM paid_invitations WHERE discord_id = %s LIMIT 1",
					(discord_id,),
				)
				return cur.fetchone() is not None
	except Exception as e:
		logger.warning("is_paid_invitation query failed: %s", e)
		return False


def get_student_profile(discord_id: str) -> dict[str, Any] | None:
	"""既存の学生プロフィール取得"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, student_number, name, furigana, department, gender, phone, email_aoyama
				FROM student_profiles
				WHERE discord_id = %s
				""",
				(discord_id,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"student_number": row[1],
				"name": row[2],
				"furigana": row[3],
				"department": row[4],
				"gender": row[5],
				"phone": row[6],
				"email_aoyama": row[7],
			}


def get_latest_otp(discord_id: str, unverified_only: bool = True) -> dict[str, Any] | None:
	"""最新の OTP レコード取得"""
	condition = "AND verified = FALSE" if unverified_only else ""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				f"""
				SELECT id, email_aoyama, code, attempt_count, verified, expires_at
				FROM otp_records
				WHERE discord_id = %s {condition}
				ORDER BY created_at DESC
				LIMIT 1
				""",
				(discord_id,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"email_aoyama": row[1],
				"code": row[2],
				"attempt_count": row[3],
				"verified": row[4],
				"expires_at": row[5],
			}


def create_otp_record(
	otp_id: str,
	discord_id: str,
	email_aoyama: str,
	otp_code: str,
	otp_expires_at: datetime,
) -> None:
	"""新しい学生OTPレコードを作成"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO otp_records (id, discord_id, email_aoyama, code, expires_at)
				VALUES (%s, %s, %s, %s, %s)
				""",
				(otp_id, discord_id, email_aoyama, otp_code, otp_expires_at),
			)
			conn.commit()


def increment_otp_attempt(otp_id: str) -> None:
	"""OTP試行回数をインクリメント"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"UPDATE otp_records SET attempt_count = attempt_count + 1 WHERE id = %s",
				(otp_id,),
			)
			conn.commit()


def mark_otp_verified(otp_id: str) -> None:
	"""OTPを検証済みに更新"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE otp_records
				SET verified = TRUE, verified_at = now()
				WHERE id = %s
				""",
				(otp_id,),
			)
			conn.commit()


def get_latest_verified_otp(discord_id: str) -> dict[str, Any] | None:
	"""プロフィール保存時のOTP検証チェック用"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, verified, verified_at, expires_at
				FROM otp_records
				WHERE discord_id = %s
				ORDER BY created_at DESC
				LIMIT 1
				""",
				(discord_id,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"verified": row[1],
				"verified_at": row[2],
				"expires_at": row[3],
			}


def upsert_student_profile_and_promote(
	profile_id: str,
	discord_id: str,
	student_number: str,
	name: str,
	furigana: str,
	department: str,
	gender: str,
	phone: str,
	email_aoyama: str,
	member_role_ids: list[str],
) -> str:
	"""学生プロフィールを保存し、pre_memberからmemberへ昇格、ロール割り当てを追加する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			# 既存プロフィールを確認
			cur.execute(
				"SELECT id FROM student_profiles WHERE discord_id = %s",
				(discord_id,),
			)
			existing = cur.fetchone()

			if existing:
				cur.execute(
					"""
					UPDATE student_profiles
					SET student_number = %s, name = %s, furigana = %s, department = %s,
						gender = %s, phone = %s, email_aoyama = %s, email_verified = TRUE,
						email_verified_at = now(), profile_submitted_at = now(), updated_at = now()
					WHERE discord_id = %s
					""",
					(
						student_number, name, furigana, department,
						gender, phone, email_aoyama, discord_id,
					),
				)
				final_profile_id = existing[0]
			else:
				cur.execute(
					"""
					INSERT INTO student_profiles
					(id, discord_id, student_number, name, furigana, department, gender, phone,
					 email_aoyama, email_verified, email_verified_at, profile_submitted_at)
					VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, now(), now())
					""",
					(
						profile_id, discord_id, student_number, name, furigana,
						department, gender, phone, email_aoyama,
					),
				)
				final_profile_id = profile_id

			# ロール変更：pre_memberからmemberへ
			cur.execute(
				"""
				UPDATE user_memberships
				SET membership_type = 'member', assigned_at = now()
				WHERE discord_id = %s AND membership_type = 'pre_member'
				""",
				(discord_id,),
			)

			for role_id in member_role_ids:
				cur.execute(
					"""
					INSERT INTO role_member_assignments (role_id, user_id)
					VALUES (%s, %s)
					ON CONFLICT DO NOTHING
					""",
					(role_id, discord_id),
				)

			conn.commit()
			return final_profile_id
