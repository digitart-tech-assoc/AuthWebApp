"""Brevo email service for OTP delivery"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BrevoClient:
	"""Brevo transactional email API client"""

	def __init__(self):
		self.api_key = os.getenv("BREVO_API_KEY")
		self.sender_email = os.getenv("BREVO_SENDER_EMAIL", "noreply@example.com")
		self.sender_name = os.getenv("BREVO_SENDER_NAME", "Digitart Technology Society")
		self.base_url = "https://api.brevo.com/v3"

		if not self.api_key:
			raise ValueError("BREVO_API_KEY environment variable not set")

	async def send_otp_email(
		self,
		email: str,
		code: str,
		name: str,
		form_type: str,
	) -> dict[str, Any]:
		"""Send OTP code via email using Brevo API

		Args:
			email: recipient email
			code: 6-digit OTP code
			name: recipient name
			form_type: "prospective-student" or "contact"

		Returns:
			{"message_id": "...", "status": "success"} or {"error": "..."}
		"""
		subject = "メール認証コード - Digitart"
		
		# HTML body
		html_body = f"""
		<html>
		<body style="font-family: Arial, sans-serif; color: #333;">
			<h2 style="color: #2563eb;">メール認証コード</h2>
			<p>こんにちは {name} さん、</p>
			<p>以下の認証コードを 15 分以内に入力してください。</p>
			<div style="background-color: #f0f0f0; padding: 20px; text-align: center; border-radius: 8px;">
				<h1 style="letter-spacing: 0.5em; color: #0f172a;">{code}</h1>
			</div>
			<p style="color: #64748b;">このメールに心当たりがない場合は、このメッセージを無視してください。</p>
			<hr style="border: none; border-top: 1px solid #e5e7eb;">
			<p style="font-size: 12px; color: #94a3b8;">
				Digitart Technology Association<br>
				© 2026 All rights reserved.
			</p>
		</body>
		</html>
		"""

		# Text fallback
		text_body = f"""
メール認証コード - Digitart

こんにちは {name} さん、

以下の認証コードを 15 分以内に入力してください：

{code}

このメールに心当たりがない場合は、このメッセージを無視してください。

---
Digitart Technology Association
© 2026 All rights reserved.
		"""

		# Ensure recipient name is present for Brevo API (some templates require it)
		recipient_name = (name or "").strip()
		if not recipient_name:
			# fallback to local-part of email if name is missing
			recipient_name = email.split("@")[0]

		payload = {
			"sender": {"email": self.sender_email, "name": self.sender_name},
			"to": [{"email": email, "name": recipient_name}],
			"subject": subject,
			"htmlContent": html_body,
			"textContent": text_body,
			"replyTo": {"email": self.sender_email},
		}

		headers = {
			"api-key": self.api_key,
			"Content-Type": "application/json",
		}

		try:
			async with httpx.AsyncClient(timeout=10.0) as client:
				response = await client.post(
					f"{self.base_url}/smtp/email",
					json=payload,
					headers=headers,
				)
				# Inspect response for debugging: Brevo returns 201 on success, 4xx/5xx on errors
				if response.status_code >= 400:
					text = response.text
					logger.error(f"Brevo API returned error: status={response.status_code} body={text}")
					return {"error": f"{response.status_code} {text}", "status": "failed"}
				try:
					data = response.json()
				except Exception:
					data = {}
				return {
					"message_id": data.get("messageId") or data.get("message_id"),
					"status": "success",
				}
		except httpx.HTTPError as e:
			logger.error(f"Brevo API error: {e}", exc_info=True)
			return {"error": str(e), "status": "failed"}
		except Exception as e:
			logger.error(f"Unexpected error sending OTP email: {e}", exc_info=True)
			return {"error": str(e), "status": "failed"}

	async def send_invite_email(self, email: str, invite_url: str, name: str, form_type: str) -> dict[str, Any]:
		"""Send Discord invite link via email using Brevo API

		Args:
			email: recipient email
			invite_url: full URL to the Discord invite
			name: recipient name
			form_type: form identifier for context
		Returns:
			{"message_id": "...", "status": "success"} or {"error": "..."}
		"""
		subject = "Discord招待リンク - Digitart"

		html_body = f"""
		<html>
		<body style="font-family: Arial, sans-serif; color: #333;">
			<h2 style="color: #2563eb;">Discord 招待リンク</h2>
			<p>こんにちは {name} さん、</p>
			<p>認証が完了しました。以下のリンクから Discord サーバーに参加してください（招待は一度のみ使用可能、期限あり(7日間)）。</p>
			<div style="background-color: #f8fafc; padding: 16px; border-radius: 8px;">
				<p style="margin:0;"><a href=\"{invite_url}\" target=\"_blank\" rel=\"noreferrer\">{invite_url}</a></p>
			</div>
			<p style="color: #64748b;">問題がある場合はこのメールに返信してください。</p>
			<hr style="border: none; border-top: 1px solid #e5e7eb;">
			<p style="font-size: 12px; color: #94a3b8;">
				Digitart Technology Association<br>
				© 2026 All rights reserved.
			</p>
		</body>
		</html>
		"""

		text_body = f"""
        Discord 招待リンク - Digitart

        こんにちは {name} さん、

        認証が完了しました。以下のリンクから Discord サーバーに参加してください：

        {invite_url}

        ---
        Digitart Technology Association
        © 2026 All rights reserved.
		"""

		recipient_name = (name or "").strip()
		if not recipient_name:
			recipient_name = email.split("@")[0]

		payload = {
			"sender": {"email": self.sender_email, "name": self.sender_name},
			"to": [{"email": email, "name": recipient_name}],
			"subject": subject,
			"htmlContent": html_body,
			"textContent": text_body,
			"replyTo": {"email": self.sender_email},
		}

		headers = {
			"api-key": self.api_key,
			"Content-Type": "application/json",
		}

		try:
			async with httpx.AsyncClient(timeout=10.0) as client:
				response = await client.post(
					f"{self.base_url}/smtp/email",
					json=payload,
					headers=headers,
				)
				if response.status_code >= 400:
					text = response.text
					logger.error(f"Brevo invite email error: status={response.status_code} body={text}")
					return {"error": f"{response.status_code} {text}", "status": "failed"}
				try:
					data = response.json()
				except Exception:
					data = {}
				return {"message_id": data.get("messageId") or data.get("message_id"), "status": "success"}
		except httpx.HTTPError as e:
			logger.error(f"Brevo API error sending invite: {e}", exc_info=True)
			return {"error": str(e), "status": "failed"}
		except Exception as e:
			logger.error(f"Unexpected error sending invite email: {e}", exc_info=True)
			return {"error": str(e), "status": "failed"}
