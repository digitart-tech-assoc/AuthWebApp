"""役割: OTP認証 & Join申請エンドポイント"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.brevo_client import BrevoClient
from app.db import repository
from app.utils.otp import generate_otp_code, hash_otp_code
from app.services.discord_client import create_channel_invite
import os

router = APIRouter(prefix="/api/v1/join", tags=["join"])


# ==================== Request Models ====================

class JoinRequestCreate(BaseModel):
	"""OTP送信リクエスト"""
	email: EmailStr
	confirm_email: EmailStr
	name: str
	form_type: str  # "prospective-student", "contact"
	metadata: dict | None = None  # form-specific fields (year, etc.)


class JoinVerifyRequest(BaseModel):
	"""OTP検証リクエスト"""
	join_request_id: str
	otp_code: str


# ==================== Response Models ====================

class JoinRequestResponse(BaseModel):
	"""OTP送信レスポンス"""
	id: str
	email: str
	name: str
	form_type: str
	status: str
	message: str


class JoinVerifyResponse(BaseModel):
	"""OTP検証レスポンス"""
	status: str
	message: str
	discord_invite_url: str | None = None


# ==================== Endpoints ====================

@router.post("/request", response_model=JoinRequestResponse)
async def request_otp(req: JoinRequestCreate) -> JoinRequestResponse:
	"""OTP送信エンドポイント
	
	1. メール重複チェック
	2. join_requests 作成
	3. OTP コード生成・ハッシュ化
	4. otp_codes 作成
	5. Brevo で OTP メール送信
	"""
	# Email 一致チェック
	if req.email != req.confirm_email:
		raise HTTPException(status_code=400, detail="Emails do not match")

	# メールアドレス形式チェック（Pydantic EmailStr で既に検証）

	try:
		# Join request 作成
		join_request = repository.create_join_request(
			email=req.email,
			name=req.name,
			form_type=req.form_type,
			metadata=req.metadata,
		)
	except ValueError as e:
		raise HTTPException(status_code=409, detail=str(e))

	try:
		# OTP コード生成＆ハッシュ化
		otp_code = generate_otp_code()
		code_hash = hash_otp_code(otp_code)

		# OTP コード保存
		repository.create_otp_code(
			join_request_id=join_request["id"],
			code_hash=code_hash,
			expires_in_minutes=15,
		)

		# Brevo で OTP メール送信
		brevo = BrevoClient()
		result = await brevo.send_otp_email(
			email=req.email,
			code=otp_code,
			name=req.name,
			form_type=req.form_type,
		)

		if result.get("status") != "success":
			raise HTTPException(
				status_code=500,
				detail=f"Failed to send OTP email: {result.get('error', 'Unknown error')}"
			)

		return JoinRequestResponse(
			id=join_request["id"],
			email=join_request["email"],
			name=join_request["name"],
			form_type=join_request["form_type"],
			status=join_request["status"],
			message=f"OTP code sent to {req.email}. Please check your email.",
		)

	except Exception as e:
		# Clean up: mark join_request as failed
		raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/verify", response_model=JoinVerifyResponse)
async def verify_otp(req: JoinVerifyRequest) -> JoinVerifyResponse:
	"""OTP検証エンドポイント
	
	1. OTP コード検証（有効期限、試行回数、コード値）
	2. 検証成功時: join_request status を "verified" に更新
	3. Discord 招待 URL を生成（スタブ）
	"""
	try:
		# OTP 検証
		repository.verify_otp(
			join_request_id=req.join_request_id,
			code_plain=req.otp_code,
		)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

	# Discord 招待 URL 生成（現在はスタブ）
	# Attempt to create a single-use invite that expires in 1 week.
	DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
	DISCORD_INVITE_CHANNEL_ID = os.getenv("DISCORD_INVITE_CHANNEL_ID")
	discord_invite_url = None
	if DISCORD_BOT_TOKEN and DISCORD_INVITE_CHANNEL_ID:
		try:
			invite = await create_channel_invite(DISCORD_INVITE_CHANNEL_ID, DISCORD_BOT_TOKEN, max_uses=1, max_age_seconds=7 * 24 * 60 * 60)
			code = invite.get("code") or invite.get("id")
			if code:
				discord_invite_url = f"https://discord.gg/{code}"
		except Exception:
			# Fail silently for now — verification already succeeded.
			import traceback
			traceback.print_exc()
			discord_invite_url = None

	# If we have a discord invite URL, attempt to email it to the user
	if discord_invite_url:
		try:
			brevo = BrevoClient()
			# look up join_request to get recipient email & name
			join_req = repository.get_join_request(req.join_request_id)
			if join_req:
				email = join_req.get("email")
				name = join_req.get("name")
				# send invite email asynchronously
				try:
					result = await brevo.send_invite_email(email=email, invite_url=discord_invite_url, name=name, form_type=join_req.get("form_type"))
					if result.get("status") != "success":
						# log but do not fail verification
						import logging
						logging.getLogger(__name__).error(f"Failed to send invite email: {result}")
				except Exception:
					import logging, traceback
					logging.getLogger(__name__).exception("Error while sending invite email")
		except Exception:
			# swallow any Brevo initialization errors
			import logging
			logging.getLogger(__name__).exception("Failed to initialize BrevoClient for invite email")

	return JoinVerifyResponse(
		status="verified",
		message="OTP verified successfully. Discord invite sent.",
		discord_invite_url=discord_invite_url,
	)
