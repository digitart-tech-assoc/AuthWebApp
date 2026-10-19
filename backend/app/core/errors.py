"""役割: ログ・エラーレスポンス向けの例外の扱い（docs/logging-and-errors.md）

- API のエラーレスポンスには例外メッセージを含めず、固定文言だけを返す（§3.2）。
- 個人情報を扱う処理（入会申請・学生登録・アンケート・お問い合わせ等）の例外は、メッセージに
  個人情報が含まれうる（DB の制約違反の `Key (email)=(...)`、メール送信 API の応答本文等）ため、
  メッセージを除いてログに出す（§3.1）。
"""

from __future__ import annotations

import logging
import traceback


def _status_code(exc: BaseException) -> int | None:
	status_code = getattr(exc, "status_code", None)
	if isinstance(status_code, int):
		return status_code
	response = getattr(exc, "response", None)
	status_code = getattr(response, "status_code", None)
	return status_code if isinstance(status_code, int) else None


def describe_exception(exc: BaseException) -> str:
	"""例外を、メッセージを含めずに表す（型名・HTTP ステータス・DB のエラーコード）。"""
	parts = [type(exc).__name__]
	status_code = _status_code(exc)
	if status_code is not None:
		parts.append(f"HTTP {status_code}")
	pgcode = getattr(exc, "pgcode", None)
	if isinstance(pgcode, str) and pgcode:
		parts.append(f"pgcode={pgcode}")
	return " ".join(parts)


def log_exception_without_message(
	logger: logging.Logger,
	operation: str,
	exc: BaseException,
	*,
	level: int = logging.ERROR,
) -> None:
	"""例外メッセージを除き、型名とスタックトレース（呼び出し履歴のみ）をログに出す。"""
	stack = "".join(traceback.format_tb(exc.__traceback__)).rstrip()
	logger.log(level, "%s failed (%s)\n%s", operation, describe_exception(exc), stack)
