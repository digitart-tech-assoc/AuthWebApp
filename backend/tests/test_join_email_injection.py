"""申請者が入力した name がメールに混入しないこと、および join 申請の name の入力検証のテスト"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1 import join as join_api
from app.api.v1 import student as student_api
from app.services.brevo_client import BrevoClient
from tests.request_factory import make_request

NAME_MARKER = "name-marker"
MALICIOUS_NAME = f'<a href="https://attacker.example/">{NAME_MARKER}</a>'
RECIPIENT = "recipient@example.com"


def make_client(captured: list[dict]) -> BrevoClient:
	"""送信処理だけを差し替えた本物の BrevoClient を作る（呼び出し元の引数の不一致も検出できる）"""
	client = BrevoClient.__new__(BrevoClient)
	client.api_key = "test_key"
	client.base_url = "https://api.brevo.com/v3"
	client.sender_email = "sender@example.com"
	client.sender_name = "Test Sender"

	async def fake_send_smtp_email(payload, operation_name):
		captured.append(payload)
		return {"status": "success", "message_id": "msg-123"}

	client._send_smtp_email = fake_send_smtp_email
	return client


def make_join_request(name: object) -> join_api.JoinRequestCreate:
	return join_api.JoinRequestCreate(
		email=RECIPIENT,
		confirm_email=RECIPIENT,
		name=name,
		form_type="contact",
	)


def assert_name_not_in_email(payload: dict) -> None:
	assert NAME_MARKER not in payload["htmlContent"]
	assert NAME_MARKER not in payload["textContent"]
	assert NAME_MARKER not in payload["to"][0]["name"]


@pytest.mark.asyncio
async def test_join_request_does_not_put_name_in_otp_email(monkeypatch):
	"""name は DB に保存するが、OTP メールには入らない"""
	saved: dict = {}
	captured: list[dict] = []

	def fake_create_join_request(**kwargs):
		saved.update(kwargs)
		return {
			"id": "request-id",
			"email": kwargs["email"],
			"name": kwargs["name"],
			"form_type": kwargs["form_type"],
			"status": "pending",
		}

	async def no_rate_limit(*args, **kwargs):
		return None

	monkeypatch.setattr(join_api, "enforce_rate_limit", no_rate_limit)
	monkeypatch.setattr(join_api.repository, "create_join_request", fake_create_join_request)
	monkeypatch.setattr(join_api.repository, "create_otp_code", lambda **kwargs: None)
	monkeypatch.setattr(join_api, "hash_otp_code", lambda code: "hashed")
	monkeypatch.setattr(join_api, "BrevoClient", lambda: make_client(captured))

	await join_api.request_otp(make_join_request(MALICIOUS_NAME), make_request())

	assert saved["name"] == MALICIOUS_NAME
	assert len(captured) == 1
	assert_name_not_in_email(captured[0])
	assert captured[0]["to"] == [{"email": RECIPIENT, "name": "recipient"}]


@pytest.mark.asyncio
async def test_join_verify_does_not_put_stored_name_in_invite_email(monkeypatch):
	"""修正前に保存された name にタグが残っていても、招待メールには入らない"""
	captured: list[dict] = []

	async def fake_create_channel_invite(*args, **kwargs):
		return {"code": "invite-code"}

	monkeypatch.setenv("DISCORD_TOKEN", "dummy-token")
	monkeypatch.setenv("DISCORD_INVITE_CHANNEL_ID", "dummy-channel")
	monkeypatch.setattr(join_api.repository, "verify_otp", lambda **kwargs: True)
	monkeypatch.setattr(join_api, "create_channel_invite", fake_create_channel_invite)
	monkeypatch.setattr(
		join_api.repository,
		"get_join_request",
		lambda request_id: {"email": RECIPIENT, "name": MALICIOUS_NAME, "form_type": "contact"},
	)
	monkeypatch.setattr(join_api, "BrevoClient", lambda: make_client(captured))

	response = await join_api.verify_otp(
		join_api.JoinVerifyRequest(join_request_id="request-id", otp_code="000000")
	)

	assert response.discord_invite_url == "https://discord.gg/invite-code"
	assert len(captured) == 1
	assert_name_not_in_email(captured[0])
	assert "https://discord.gg/invite-code" in captured[0]["htmlContent"]


@pytest.mark.asyncio
async def test_student_send_otp_does_not_put_name_in_otp_email(monkeypatch):
	"""本登録の OTP メールにも name は入らない"""
	captured: list[dict] = []

	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)
	monkeypatch.setattr(student_api, "hash_otp_code", lambda code: "hashed")
	monkeypatch.setattr(student_api.student_repository, "create_otp_record", lambda *args: None)
	monkeypatch.setattr(student_api, "BrevoClient", lambda: make_client(captured))

	await student_api.send_otp(
		student_api.SendOTPRequest(student_number="S0000000", name=MALICIOUS_NAME),
		principal={"discord_id": "000000000000000000", "sub": "internal-user-id"},
	)

	assert len(captured) == 1
	assert_name_not_in_email(captured[0])


@pytest.mark.asyncio
async def test_invite_email_escapes_url_in_html_only():
	captured: list[dict] = []
	invite_url = 'https://discord.gg/abc?a=1&b="><img src=x>'

	await make_client(captured).send_invite_email(email=RECIPIENT, invite_url=invite_url, form_type="contact")

	html_content = captured[0]["htmlContent"]
	assert invite_url not in html_content
	assert "<img" not in html_content
	assert "https://discord.gg/abc?a=1&amp;b=&quot;&gt;&lt;img src=x&gt;" in html_content
	assert invite_url in captured[0]["textContent"]


@pytest.mark.parametrize(
	"name",
	[
		"",
		"   ",
		"a" * 101,
		"テスト\n太郎",
		"テスト\x00太郎",
		"テスト‮太郎",
	],
)
def test_join_request_rejects_invalid_name(name):
	with pytest.raises(ValidationError):
		make_join_request(name)


@pytest.mark.parametrize("name", ["テスト 太郎", "a" * 100])
def test_join_request_accepts_valid_name(name):
	assert make_join_request(name).name == name


def test_join_request_strips_surrounding_whitespace():
	assert make_join_request("  テスト 太郎  ").name == "テスト 太郎"
