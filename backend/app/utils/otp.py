"""OTP generation and hashing utilities"""

from __future__ import annotations

import secrets
import bcrypt


def generate_otp_code() -> str:
	"""Generate a random 6-digit OTP code"""
	return "".join(secrets.choice("0123456789") for _ in range(6))


def hash_otp_code(code: str) -> str:
	"""Hash OTP code with bcrypt

	Args:
		code: plaintext 6-digit code

	Returns:
		bcrypt hash (bytes decoded as str)
	"""
	salt = bcrypt.gensalt(rounds=10)
	hashed = bcrypt.hashpw(code.encode(), salt)
	return hashed.decode()


def verify_otp_code(code: str, code_hash: str) -> bool:
	"""Verify OTP code against hash

	Args:
		code: plaintext code entered by user
		code_hash: stored bcrypt hash

	Returns:
		True if matches, False otherwise
	"""
	try:
		return bcrypt.checkpw(code.encode(), code_hash.encode())
	except Exception:
		return False
