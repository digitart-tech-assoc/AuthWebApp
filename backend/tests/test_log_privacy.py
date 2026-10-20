"""ログに個人情報と OTP を出さないことのテスト（#146）

- ログ出力（logger.* / _log_db_access / print）に Discord ID・学生番号・メールアドレス・OTP を渡さない
- ログイン中の本人は内部 ID（principal["sub"]）で示す
- _log_db_access のペイロードに個人情報と入力された OTP を含めない
"""

import ast
import logging
from pathlib import Path

import pytest

from app.api.v1 import student as student_api
from app.db import connection
from app.db import otp_repository
from app.services.discord_client import redact_snowflakes
from tests.request_factory import make_request

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# ログ出力に渡してはいけない変数名
FORBIDDEN_NAMES = {
	"discord_id", "user_id", "uid", "student_number", "email", "email_aoyama",
	"code", "code_plain", "otp_code", "principal", "_principal",
	# 認証情報（docs/logging-and-errors.md §1.2）
	"token", "authorization", "SHARED_SECRET", "shared_secret", "SUPABASE_JWT_SECRET",
}
# ログ出力に渡してはいけない属性名（req.student_number など）
FORBIDDEN_ATTRS = {"discord_id", "student_number", "email", "email_aoyama"}
# ログ出力の中で、添字（member["discord_id"] など）や辞書のキーとして使ってはいけない文字列
FORBIDDEN_KEYS = {"discord_id", "student_number", "email", "email_aoyama", "code_preview"}
# _log_db_access のペイロードのキーとして使ってはいけない文字列（ロール名の r["name"] などは対象外）
FORBIDDEN_DICT_KEYS = FORBIDDEN_KEYS | {"name"}
# user_repository の user_id は Supabase のユーザー ID（内部 ID）なので許可する
ALLOWED = {("app/db/user_repository.py", "user_id")}

FAKE_DISCORD_ID = "123456789012345678"
FAKE_STUDENT_NUMBER = "1A234567"
FAKE_EMAIL = "applicant@example.com"


def _is_log_call(node: ast.Call) -> bool:
	func = node.func
	if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "logger":
		return True
	return isinstance(func, ast.Name) and func.id in {"_log_db_access", "print"}


def _is_principal_sub(node: ast.AST) -> bool:
	"""principal.get("sub") / _principal.get("sub")（内部 ID）なら True"""
	return (
		isinstance(node, ast.Call)
		and isinstance(node.func, ast.Attribute)
		and node.func.attr == "get"
		and isinstance(node.func.value, ast.Name)
		and node.func.value.id in {"principal", "_principal"}
		and len(node.args) == 1
		and isinstance(node.args[0], ast.Constant)
		and node.args[0].value == "sub"
	)


def _violations(node: ast.AST) -> list[str]:
	if _is_principal_sub(node):
		return []
	found = []
	if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
		found.append(node.id)
	if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
		found.append(f".{node.attr}")
	if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in FORBIDDEN_KEYS:
		found.append(f"[{node.slice.value!r}]")
	if isinstance(node, ast.Dict):
		found.extend(
			f"{{{key.value!r}: ...}}"
			for key in node.keys
			if isinstance(key, ast.Constant) and key.value in FORBIDDEN_DICT_KEYS
		)
	for child in ast.iter_child_nodes(node):
		found.extend(_violations(child))
	return found


def test_log_calls_do_not_receive_personal_information():
	violations = []
	for path in sorted(APP_DIR.rglob("*.py")):
		relative = path.relative_to(APP_DIR.parent).as_posix()
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		for node in ast.walk(tree):
			if not (isinstance(node, ast.Call) and _is_log_call(node)):
				continue
			for arg in [*node.args, *(keyword.value for keyword in node.keywords)]:
				for name in _violations(arg):
					if (relative, name) not in ALLOWED:
						violations.append(f"{relative}:{node.lineno} {name}")

	assert violations == []


def test_redact_snowflakes_hides_discord_ids_in_messages():
	message = f"Client error '404 Not Found' for url '/guilds/{FAKE_DISCORD_ID}/members/{FAKE_DISCORD_ID}'"

	assert FAKE_DISCORD_ID not in redact_snowflakes(message)
	assert "/members/:id" in redact_snowflakes(message)


@pytest.mark.asyncio
async def test_send_otp_logs_internal_id_instead_of_personal_information(monkeypatch, caplog):
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)
	monkeypatch.setattr(student_api, "hash_otp_code", lambda code: "hashed")
	monkeypatch.setattr(student_api.student_repository, "create_otp_record", lambda *args: None)

	class FakeBrevoClient:
		async def send_otp_email(self, **kwargs):
			return {"status": "success"}

	monkeypatch.setattr(student_api, "BrevoClient", FakeBrevoClient)

	with caplog.at_level(logging.DEBUG):
		await student_api.send_otp(
			student_api.SendOTPRequest(student_number=FAKE_STUDENT_NUMBER, name="テスト 太郎"),
			request=make_request(),
			principal={"discord_id": FAKE_DISCORD_ID, "sub": "internal-user-id"},
		)

	assert "internal-user-id" in caplog.text
	assert FAKE_DISCORD_ID not in caplog.text
	assert FAKE_STUDENT_NUMBER not in caplog.text


class _StopAfterLog(Exception):
	"""_log_db_access の後の DB アクセスを止めるための例外"""


def _stop(*args, **kwargs):
	raise _StopAfterLog


def test_create_join_request_db_log_excludes_personal_information(monkeypatch, capsys):
	monkeypatch.setattr(connection, "_should_log_to_stdout", lambda: True)
	monkeypatch.setattr(otp_repository, "_connect", _stop)

	with pytest.raises(_StopAfterLog):
		otp_repository.create_join_request(
			email=FAKE_EMAIL,
			name="テスト 太郎",
			form_type="aoyama-student",
			metadata={"student_id": FAKE_STUDENT_NUMBER},
		)

	out = capsys.readouterr().out
	assert "create_join_request" in out
	assert FAKE_EMAIL not in out
	assert "テスト 太郎" not in out
	assert FAKE_STUDENT_NUMBER not in out


def test_verify_otp_attempt_db_log_excludes_entered_code(monkeypatch, capsys):
	class FakeCursor:
		def __enter__(self):
			return self

		def __exit__(self, *args):
			return False

		execute = staticmethod(_stop)

	class FakeConnection:
		def __enter__(self):
			return self

		def __exit__(self, *args):
			return False

		def cursor(self):
			return FakeCursor()

	monkeypatch.setattr(connection, "_should_log_to_stdout", lambda: True)
	monkeypatch.setattr(otp_repository, "_connect", lambda: FakeConnection())

	with pytest.raises(_StopAfterLog):
		otp_repository.verify_otp("request-id", "987654")

	out = capsys.readouterr().out
	assert "verify_otp_attempt" in out
	assert "987654" not in out
	assert "98****" not in out
