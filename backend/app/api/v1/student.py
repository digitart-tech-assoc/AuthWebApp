"""役割: 学生登録・入会フォーム API"""

from __future__ import annotations

import asyncio
import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_principal
from app.db.repository import _connect
from app.services.brevo_client import send_otp_email


router = APIRouter(prefix="/api/v1/student", tags=["student"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ValidateEligibilityResponse(BaseModel):
	is_discord_linked: bool
	is_pre_member: bool
	is_paid: bool
	can_register: bool
	reason: str


class SendOTPRequest(BaseModel):
	student_number: str = Field(..., pattern=r"^[Aa]\d{7}$", description="学生番号 (e.g., A2312345)")
	name: str = Field(..., min_length=1, max_length=100)


class SendOTPResponse(BaseModel):
	email_aoyama: str
	message: str
	expires_in_seconds: int


class VerifyOTPRequest(BaseModel):
	code: str = Field(..., pattern=r"^\d{6}$", description="OTPコード (6-digit)")


class VerifyOTPResponse(BaseModel):
	verified: bool
	message: str


class StudentProfileRequest(BaseModel):
	student_number: str = Field(..., pattern=r"^[Aa]\d{7}$")
	name: str = Field(..., min_length=1, max_length=100)
	furigana: str = Field(..., min_length=1, max_length=100)
	department: str = Field(..., min_length=1, max_length=100)
	gender: str | None = None
	phone: str = Field(..., pattern=r"^\d{10,11}$", description="電話番号 (10-11 digits)")


class StudentProfileResponse(BaseModel):
	profile_id: str
	student_number: str
	name: str
	email_aoyama: str
	message: str


class StudentProfileGetResponse(BaseModel):
	student_number: str
	name: str
	furigana: str
	department: str
	gender: str | None
	phone: str
	email_aoyama: str


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_student_email(student_number: str) -> str:
	"""学生番号から大学メールアドレスを生成
	Examples: A2312345 → a2312345@aoyama.ac.jp
	"""
	return f"{student_number.lower()}@aoyama.ac.jp"


def _generate_otp_code(length: int = 6) -> str:
	"""ランダムなOTPコード生成"""
	return "".join(f"{secrets.randbelow(10)}" for _ in range(length))


def _is_pre_member(discord_id: str) -> bool:
	"""Discord IDが pre_member リストにあるか確認"""
	try:
		with _connect() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"SELECT 1 FROM pre_member_list WHERE discord_id = %s LIMIT 1",
					(discord_id,),
				)
				return cur.fetchone() is not None
	except Exception:
		return False


def _is_paid_invitation(discord_id: str) -> bool:
	"""Discord IDが支払済リストにあるか確認"""
	try:
		with _connect() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"SELECT 1 FROM paid_invitations WHERE discord_id = %s LIMIT 1",
					(discord_id,),
				)
				return cur.fetchone() is not None
	except Exception:
		return False


def _get_student_profile(discord_id: str) -> dict[str, Any] | None:
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


def _get_latest_otp(discord_id: str) -> dict[str, Any] | None:
	"""最新の OTP レコード取得"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, email_aoyama, code, attempt_count, verified, expires_at
				FROM otp_records
				WHERE discord_id = %s AND verified = FALSE
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


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/validate-eligibility", response_model=ValidateEligibilityResponse)
async def validate_eligibility(
	principal: dict = Depends(get_current_principal),
) -> ValidateEligibilityResponse:
	"""入会資格を確認する。
	以下をすべて満たす必要がある：
	1. Discord がリンクされている
	2. pre_member リストに登録されている
	3. 支払済みリストに登録されている
	"""
	discord_id = principal.get("discord_id")

	if not discord_id:
		return ValidateEligibilityResponse(
			is_discord_linked=False,
			is_pre_member=False,
			is_paid=False,
			can_register=False,
			reason="Discord アカウントがリンクされていません",
		)

	is_pre_member = await asyncio.to_thread(_is_pre_member, discord_id)
	is_paid = await asyncio.to_thread(_is_paid_invitation, discord_id)

	can_register = is_pre_member and is_paid

	if not is_pre_member:
		reason = "入会予定者リストに登録されていません"
	elif not is_paid:
		reason = "入会費の支払いが確認できません"
	else:
		reason = "すべての条件を満たしています"

	return ValidateEligibilityResponse(
		is_discord_linked=True,
		is_pre_member=is_pre_member,
		is_paid=is_paid,
		can_register=can_register,
		reason=reason,
	)


@router.post("/otp/send", response_model=SendOTPResponse)
async def send_otp(
	req: SendOTPRequest,
	principal: dict = Depends(get_current_principal),
) -> SendOTPResponse:
	"""大学メールに OTP を送信する"""
	discord_id = principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=401, detail="Discord account not linked")

	email_aoyama = _generate_student_email(req.student_number)
	otp_code = _generate_otp_code()
	otp_expires_at = datetime.now(timezone.utc) + timedelta(seconds=600)  # 10 minutes

	# OTP レコードを DB に保存
	import uuid
	otp_id = f"otp_{uuid.uuid4().hex[:12]}"

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

	# メール送信
	try:
		await asyncio.to_thread(
			send_otp_email,
			email_aoyama,
			otp_code,
			req.name,
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

	return SendOTPResponse(
		email_aoyama=email_aoyama,
		message="OTP を送信しました。メールを確認してください",
		expires_in_seconds=600,
	)


@router.post("/otp/verify", response_model=VerifyOTPResponse)
async def verify_otp(
	req: VerifyOTPRequest,
	principal: dict = Depends(get_current_principal),
) -> VerifyOTPResponse:
	"""OTP コードを検証する"""
	discord_id = principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=401, detail="Discord account not linked")

	# 最新の未検証 OTP を取得
	otp = await asyncio.to_thread(_get_latest_otp, discord_id)
	if otp is None:
		raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")

	# 有効期限確認
	if otp["expires_at"] < datetime.now(timezone.utc):
		raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

	# 試行回数確認（最大3回）
	if otp["attempt_count"] >= 3:
		raise HTTPException(status_code=429, detail="Too many attempts. Please request a new OTP.")

	# OTP コード確認
	if otp["code"] != req.code:
		# 試行回数をインクリメント
		with _connect() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"UPDATE otp_records SET attempt_count = attempt_count + 1 WHERE id = %s",
					(otp["id"],),
				)
				conn.commit()

		raise HTTPException(status_code=400, detail="Incorrect OTP code.")

	# OTP を検証済みにする
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE otp_records
				SET verified = TRUE, verified_at = now()
				WHERE id = %s
				""",
				(otp["id"],),
			)
			conn.commit()

	return VerifyOTPResponse(
		verified=True,
		message="OTP 認証完了",
	)


@router.post("/profile", response_model=StudentProfileResponse)
async def create_student_profile(
	req: StudentProfileRequest,
	principal: dict = Depends(get_current_principal),
) -> StudentProfileResponse:
	"""学生プロフィールを保存する"""
	discord_id = principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=401, detail="Discord account not linked")

	# OTP が検証済みか確認
	otp = await asyncio.to_thread(_get_latest_otp, discord_id)
	if otp is None or not otp["verified"]:
		raise HTTPException(status_code=400, detail="OTP verification required")

	email_aoyama = _generate_student_email(req.student_number)

	import uuid
	profile_id = f"prof_{uuid.uuid4().hex[:12]}"

	# プロフィールを保存（upsert）
	with _connect() as conn:
		with conn.cursor() as cur:
			# 既存プロフィールを確認
			cur.execute(
				"SELECT id FROM student_profiles WHERE discord_id = %s",
				(discord_id,),
			)
			existing = cur.fetchone()

			if existing:
				# 更新
				cur.execute(
					"""
					UPDATE student_profiles
					SET student_number = %s, name = %s, furigana = %s, department = %s,
						gender = %s, phone = %s, email_aoyama = %s, email_verified = TRUE,
						email_verified_at = now(), profile_submitted_at = now(), updated_at = now()
					WHERE discord_id = %s
					""",
					(
						req.student_number,
						req.name,
						req.furigana,
						req.department,
						req.gender,
						req.phone,
						email_aoyama,
						discord_id,
					),
				)
				profile_id = existing[0]
			else:
				# 新規作成
				cur.execute(
					"""
					INSERT INTO student_profiles
					(id, discord_id, student_number, name, furigana, department, gender, phone,
					 email_aoyama, email_verified, email_verified_at, profile_submitted_at)
					VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, now(), now())
					""",
					(
						profile_id,
						discord_id,
						req.student_number,
						req.name,
						req.furigana,
						req.department,
						req.gender,
						req.phone,
						email_aoyama,
					),
				)

			conn.commit()

	return StudentProfileResponse(
		profile_id=profile_id,
		student_number=req.student_number,
		name=req.name,
		email_aoyama=email_aoyama,
		message="登録完了。本会員として登録されました",
	)


@router.get("/profile", response_model=StudentProfileGetResponse)
async def get_student_profile(
	principal: dict = Depends(get_current_principal),
) -> StudentProfileGetResponse:
	"""Pre-member として登録済みの学生情報を取得する"""
	discord_id = principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=401, detail="Discord account not linked")

	profile = await asyncio.to_thread(_get_student_profile, discord_id)
	if profile is None:
		raise HTTPException(status_code=404, detail="Profile not found")

	return StudentProfileGetResponse(
		student_number=profile["student_number"],
		name=profile["name"],
		furigana=profile["furigana"],
		department=profile["department"],
		gender=profile["gender"],
		phone=profile["phone"],
		email_aoyama=profile["email_aoyama"],
	)
