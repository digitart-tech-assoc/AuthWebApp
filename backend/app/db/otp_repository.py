"""役割: 入会申請（Join Requests）およびOTP認証に関する永続化処理"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.config import OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS
from app.db.connection import _connect, _log_db_access
from app.utils.otp import verify_otp_code


def create_join_request(
	email: str,
	name: str,
	form_type: str,
	metadata: dict | None = None,
) -> dict[str, Any]:
	"""Create a join request entry

	Args:
		email: applicant email
		name: applicant name
		form_type: "prospective-student" or "contact"
		metadata: form-specific data (year, etc.)

	Returns:
		{"id": "...", "email": "...", "status": "pending", ...}

	Raises:
		ValueError: if email already exists
	"""
	request_id = str(uuid4())

	_log_db_access("create_join_request", {"email": email, "name": name, "form_type": form_type, "metadata": metadata})
	with _connect() as conn:
		with conn.cursor() as cur:
			try:
				# まず既存レコードを確認する
				cur.execute(
					"SELECT id, status, name, form_type, metadata, created_at, updated_at FROM join_requests WHERE email = %s",
					(email,)
				)
				existing = cur.fetchone()
				if existing:
					existing_id, existing_status = existing[0], existing[1]
					# pending/failed の場合は既存レコードを更新して再利用する
					if existing_status in ("pending", "failed"):
						cur.execute(
							"""
							UPDATE join_requests
							SET name = %s, form_type = %s, metadata = %s, status = 'pending', updated_at = now()
							WHERE id = %s
							RETURNING id, email, name, form_type, status, metadata, created_at, updated_at
							""",
							(name, form_type, json.dumps(metadata or {}), existing_id),
						)
						row = cur.fetchone()
						if row is None:
							raise RuntimeError("Failed to update existing join request")
						conn.commit()
						return {
							"id": row[0],
							"email": row[1],
							"name": row[2],
							"form_type": row[3],
							"status": row[4],
							"metadata": row[5],
							"created_at": row[6].isoformat() if row[6] else None,
							"updated_at": row[7].isoformat() if row[7] else None,
						}
					# verified/completed 等は既存登録として扱いエラーを返す
					raise ValueError(f"Email {email} already registered")

				# 存在しなければ新規挿入
				cur.execute(
					"""
					INSERT INTO join_requests (id, email, name, form_type, metadata, status)
					VALUES (%s, %s, %s, %s, %s, 'pending')
					RETURNING id, email, name, form_type, status, metadata, created_at, updated_at
					""",
					(request_id, email, name, form_type, json.dumps(metadata or {})),
				)
				row = cur.fetchone()
				if row is None:
					raise RuntimeError("Failed to create join request")
				conn.commit()
				return {
					"id": row[0],
					"email": row[1],
					"name": row[2],
					"form_type": row[3],
					"status": row[4],
					"metadata": row[5],
					"created_at": row[6].isoformat() if row[6] else None,
					"updated_at": row[7].isoformat() if row[7] else None,
				}
			except Exception as e:
				conn.rollback()
				if "unique" in str(e).lower():
					raise ValueError(f"Email {email} already registered") from e
				raise


def create_otp_code(
	join_request_id: str,
	code_hash: str,
	expires_in_minutes: int = OTP_EXPIRY_MINUTES,
) -> dict[str, Any]:
	"""Create an OTP code entry

	Args:
		join_request_id: FK to join_requests.id
		code_hash: bcrypt hash of OTP
		expires_in_minutes: OTP validity (default 15)

	Returns:
		{"id": "...", "join_request_id": "...", "expires_at": ...}
	"""
	otp_id = str(uuid4())
	# Use timezone-aware UTC datetime for expires_at
	expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

	with _connect() as conn:
		with conn.cursor() as cur:
			_log_db_access("create_otp_code", {"join_request_id": join_request_id, "otp_id": otp_id, "expires_in_minutes": expires_in_minutes})
			cur.execute(
				"""
				INSERT INTO otp_codes (id, join_request_id, code_hash, expires_at)
				VALUES (%s, %s, %s, %s)
				RETURNING id, join_request_id, expires_at, created_at
				""",
				(otp_id, join_request_id, code_hash, expires_at),
			)
			row = cur.fetchone()
			conn.commit()
			return {
				"id": row[0],
				"join_request_id": row[1],
				"expires_at": row[2].isoformat() if row[2] else None,
				"created_at": row[3].isoformat() if row[3] else None,
			}


def verify_otp(join_request_id: str, code_plain: str) -> bool:
	"""Verify OTP code against stored hash

	Args:
		join_request_id: join request ID
		code_plain: plaintext 6-digit code entered by user

	Returns:
		True if valid and not expired/max attempts exceeded

	Raises:
		ValueError: if expired or max attempts exceeded
	"""
	with _connect() as conn:
		with conn.cursor() as cur:
			_log_db_access("verify_otp_attempt", {"join_request_id": join_request_id, "code_preview": (code_plain[:2] + "****") if code_plain else ""})
			# Get latest unverified OTP for this join request
			cur.execute(
				"""
				SELECT id, code_hash, expires_at, attempt_count, verified_at
				FROM otp_codes
				WHERE join_request_id = %s AND verified_at IS NULL
				ORDER BY created_at DESC
				LIMIT 1
				""",
				(join_request_id,),
			)
			row = cur.fetchone()
			if row is None:
				raise ValueError("No active OTP found")

			otp_id, code_hash, expires_at, attempt_count, verified_at = row

			# Normalize expires_at to timezone-aware UTC if needed, then check expiry
			if getattr(expires_at, 'tzinfo', None) is None:
				expires_at = expires_at.replace(tzinfo=timezone.utc)

			if datetime.now(timezone.utc) > expires_at:
				raise ValueError("OTP has expired")

			# Check max attempts
			if attempt_count >= OTP_MAX_ATTEMPTS:
				raise ValueError("Maximum OTP attempts exceeded")

			# Check code
			if not verify_otp_code(code_plain, code_hash):
				# Increment attempt count
				cur.execute(
					"""
					UPDATE otp_codes SET attempt_count = attempt_count + 1
					WHERE id = %s
					""",
					(otp_id,),
				)
				conn.commit()
				raise ValueError("Invalid OTP code")

			# Mark as verified
			cur.execute(
				"""
				UPDATE otp_codes SET verified_at = now()
				WHERE id = %s
				RETURNING id
				""",
				(otp_id,),
			)
			conn.commit()
			return True


def get_join_request(join_request_id: str) -> dict[str, Any] | None:
	"""Get join request by ID"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT id, email, name, form_type, status, metadata, created_at, updated_at
				FROM join_requests
				WHERE id = %s
				""",
				(join_request_id,),
			)
			row = cur.fetchone()
			if row is None:
				return None
			return {
				"id": row[0],
				"email": row[1],
				"name": row[2],
				"form_type": row[3],
				"status": row[4],
				"metadata": row[5],
				"created_at": row[6].isoformat() if row[6] else None,
				"updated_at": row[7].isoformat() if row[7] else None,
			}


def save_member_survey_response(
	profile_id: str | None,
	student_number: str,
	join_request_id: str | None,
	payload: dict[str, Any],
) -> dict[str, Any]:
	"""Save a member survey response into member_survey_responses.

	Returns the newly created record metadata.
	"""
	_log_db_access("save_member_survey_response", {"student_number": student_number})
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO member_survey_responses (
					profile_id, student_number, join_request_id,
					digitart_channels, digitart_channels_other,
					circle_search_channels, circle_search_other,
					discord_invite_source, discord_invite_other,
					interested_fields, interested_fields_other,
					motivations, motivations_other,
					raw_payload, created_at, updated_at
				) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
				RETURNING id, created_at
				""",
				(
					profile_id,
					student_number,
					join_request_id,
					json.dumps(payload.get("digitart_channels", []), ensure_ascii=False),
					payload.get("digitart_channels_other"),
					json.dumps(payload.get("circle_search_channels", []), ensure_ascii=False),
					payload.get("circle_search_other"),
					payload.get("discord_invite_source"),
					payload.get("discord_invite_other"),
					json.dumps(payload.get("interested_fields", []), ensure_ascii=False),
					payload.get("interested_fields_other"),
					json.dumps(payload.get("motivations", []), ensure_ascii=False),
					payload.get("motivations_other"),
					json.dumps(payload.get("raw_payload", payload), ensure_ascii=False),
				),
			)
			row = cur.fetchone()
			conn.commit()
			return {"id": row[0], "created_at": row[1].isoformat() if row[1] else None}
