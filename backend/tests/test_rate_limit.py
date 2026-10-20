"""レート制限のテスト（#82）

- 上限までは受け付け、超えたら次に受け付けられるまでの秒数を付けて拒否する
- 窓の外に出た記録は数えず、記録がなくなったキーは消す
- クライアント IP は X-Forwarded-For の最右端（ingress が付けた値）、なければ接続元を使う
"""

import ipaddress
import logging

import pytest
from fastapi import HTTPException

from app.api.v1 import contact as contact_api
from app.api.v1 import join as join_api
from app.api.v1 import student as student_api
from app.core.config import (
	CONTACT_RATE_LIMIT,
	JOIN_REQUEST_RATE_LIMIT,
	JOIN_REQUEST_RELAXED_RATE_LIMIT,
	OTP_SEND_RATE_LIMIT,
)
from app.core.rate_limit import (
	RateLimitExceededError,
	SlidingWindowRateLimiter,
	enforce_rate_limit,
	get_client_ip,
	is_in_networks,
)
from tests.request_factory import make_request

CLIENT_IP = "203.0.113.9"


class FakeClock:
	def __init__(self) -> None:
		self.now = 1000.0

	def __call__(self) -> float:
		return self.now


class TestSlidingWindowRateLimiter:
	@pytest.mark.asyncio
	async def test_rejects_after_limit_with_retry_after(self):
		clock = FakeClock()
		limiter = SlidingWindowRateLimiter(3, 600, clock=clock)
		for _ in range(3):
			await limiter.hit("key")
			clock.now += 10

		with pytest.raises(RateLimitExceededError) as error:
			await limiter.hit("key")
		# 最初の記録（1000）が窓の外に出る 1600 まで待つ
		assert error.value.retry_after == pytest.approx(1600 - clock.now)

	@pytest.mark.asyncio
	async def test_accepts_again_after_window(self):
		clock = FakeClock()
		limiter = SlidingWindowRateLimiter(1, 600, clock=clock)
		await limiter.hit("key")
		with pytest.raises(RateLimitExceededError):
			await limiter.hit("key")

		clock.now += 600
		await limiter.hit("key")

	@pytest.mark.asyncio
	async def test_rejected_request_is_not_counted(self):
		clock = FakeClock()
		limiter = SlidingWindowRateLimiter(1, 600, clock=clock)
		await limiter.hit("key")
		clock.now += 300
		with pytest.raises(RateLimitExceededError):
			await limiter.hit("key")

		# 拒否した 1300 の分は記録しないため、最初の記録が窓の外に出れば受け付ける
		clock.now = 1600
		await limiter.hit("key")

	@pytest.mark.asyncio
	async def test_keys_are_independent(self):
		limiter = SlidingWindowRateLimiter(1, 600, clock=FakeClock())
		await limiter.hit("a")
		await limiter.hit("b")
		with pytest.raises(RateLimitExceededError):
			await limiter.hit("a")

	@pytest.mark.asyncio
	async def test_expired_keys_are_removed(self):
		clock = FakeClock()
		limiter = SlidingWindowRateLimiter(1, 600, clock=clock)
		await limiter.hit("a")
		clock.now += 600
		await limiter.hit("b")
		assert set(limiter._hits) == {"b"}


class TestGetClientIp:
	def test_uses_rightmost_forwarded_for(self):
		request = make_request(headers={"X-Forwarded-For": "203.0.113.9, 198.51.100.7"})
		assert get_client_ip(request) == "198.51.100.7"

	def test_falls_back_to_client_host(self):
		assert get_client_ip(make_request(client_host="192.0.2.1")) == "192.0.2.1"

	def test_ignores_empty_forwarded_for(self):
		assert get_client_ip(make_request(client_host="192.0.2.1", headers={"X-Forwarded-For": " , "})) == "192.0.2.1"


class TestIsInNetworks:
	NETWORKS = [ipaddress.ip_network("133.2.0.0/16")]

	@pytest.mark.parametrize("ip", ["133.2.0.1", "133.2.255.254"])
	def test_inside(self, ip):
		assert is_in_networks(ip, self.NETWORKS)

	@pytest.mark.parametrize("ip", ["133.3.0.1", "203.0.113.9", "2001:db8::1", "unknown", ""])
	def test_outside_or_invalid(self, ip):
		assert not is_in_networks(ip, self.NETWORKS)


@pytest.mark.asyncio
async def test_enforce_returns_429_without_logging_key(caplog):
	limiter = SlidingWindowRateLimiter(1, 600, clock=FakeClock())
	await enforce_rate_limit(limiter, f"ip:{CLIENT_IP}", "contact")

	with pytest.raises(HTTPException) as error:
		await enforce_rate_limit(limiter, f"ip:{CLIENT_IP}", "contact")

	assert error.value.status_code == 429
	assert error.value.headers == {"Retry-After": "600"}
	assert "endpoint=contact" in caplog.text
	assert CLIENT_IP not in caplog.text


# ==================== エンドポイント ====================

def _forwarded_request() -> object:
	"""Server Action が X-Forwarded-For を転送してきた場合（接続元は Frontend の Pod）"""
	return make_request(client_host="10.1.0.5", headers={"X-Forwarded-For": CLIENT_IP})


class SendCounter:
	def __init__(self) -> None:
		self.count = 0

	async def send_otp_email(self, **kwargs):
		self.count += 1
		return {"status": "success"}


@pytest.fixture
def brevo(monkeypatch):
	counter = SendCounter()
	monkeypatch.setattr(student_api, "BrevoClient", lambda: counter)
	monkeypatch.setattr(join_api, "BrevoClient", lambda: counter)
	return counter


@pytest.fixture
def student_ready(monkeypatch):
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)
	monkeypatch.setattr(student_api, "hash_otp_code", lambda code: "hashed")
	monkeypatch.setattr(student_api.student_repository, "create_otp_record", lambda *args: None)


async def _send_student_otp(discord_id: str = "discord-1"):
	return await student_api.send_otp(
		student_api.SendOTPRequest(student_number="1A234567", name="テスト 太郎"),
		principal={"discord_id": discord_id, "sub": f"user-{discord_id}"},
	)


@pytest.mark.asyncio
async def test_student_otp_send_is_limited_per_discord_id(student_ready, brevo, caplog):
	for _ in range(OTP_SEND_RATE_LIMIT):
		await _send_student_otp()

	with caplog.at_level(logging.WARNING), pytest.raises(HTTPException) as error:
		await _send_student_otp()

	assert error.value.status_code == 429
	assert "Retry-After" in error.value.headers
	assert brevo.count == OTP_SEND_RATE_LIMIT
	assert "aa234567@aoyama.ac.jp" not in caplog.text

	# 同じネットワーク（IP）からでも、別の discord_id なら受け付ける
	await _send_student_otp(discord_id="discord-other")
	assert brevo.count == OTP_SEND_RATE_LIMIT + 1


def _join_request(index: int) -> join_api.JoinRequestCreate:
	email = f"applicant{index}@example.com"
	return join_api.JoinRequestCreate(email=email, confirm_email=email, name="テスト 太郎", form_type="other")


@pytest.fixture
def join_ready(monkeypatch):
	created = []
	monkeypatch.setattr(
		join_api.repository,
		"create_join_request",
		lambda **kwargs: created.append(kwargs) or {"id": "jr", "status": "pending", **kwargs},
	)
	monkeypatch.setattr(join_api.repository, "create_otp_code", lambda **kwargs: None)
	monkeypatch.setattr(join_api, "hash_otp_code", lambda code: "hashed")
	return created


async def _request_join(index: int, ip: str):
	return await join_api.request_otp(_join_request(index), make_request(headers={"X-Forwarded-For": ip}))


@pytest.mark.asyncio
async def test_join_request_is_limited_per_ip(join_ready, brevo):
	for i in range(JOIN_REQUEST_RATE_LIMIT):
		await _request_join(i, CLIENT_IP)

	with pytest.raises(HTTPException) as error:
		await _request_join(99, CLIENT_IP)

	assert error.value.status_code == 429
	# 上限に達したら申請も作らず、メールも送らない
	assert len(join_ready) == JOIN_REQUEST_RATE_LIMIT
	assert brevo.count == JOIN_REQUEST_RATE_LIMIT

	# 別の IP からは受け付ける
	await _request_join(100, "198.51.100.7")


@pytest.mark.asyncio
async def test_join_request_from_university_network_uses_relaxed_limit(join_ready, brevo):
	campus_ip = "133.2.10.20"
	for i in range(JOIN_REQUEST_RELAXED_RATE_LIMIT):
		await _request_join(i, campus_ip)

	with pytest.raises(HTTPException) as error:
		await _request_join(999, campus_ip)

	assert error.value.status_code == 429
	assert brevo.count == JOIN_REQUEST_RELAXED_RATE_LIMIT


@pytest.mark.asyncio
async def test_university_network_does_not_consume_normal_limit(join_ready, brevo):
	"""大学のネットワークからの申請は、通常の上限とは別に数える"""
	for i in range(JOIN_REQUEST_RATE_LIMIT + 1):
		await _request_join(i, "133.2.10.20")

	for i in range(JOIN_REQUEST_RATE_LIMIT):
		await _request_join(100 + i, CLIENT_IP)


@pytest.mark.asyncio
async def test_join_request_with_invalid_input_is_not_counted(monkeypatch):
	monkeypatch.setattr(join_api.repository, "create_join_request", lambda **kwargs: pytest.fail("must not create"))
	mismatch = join_api.JoinRequestCreate(
		email="a@example.com", confirm_email="b@example.com", name="テスト 太郎", form_type="other"
	)

	for _ in range(JOIN_REQUEST_RATE_LIMIT + 1):
		with pytest.raises(HTTPException) as error:
			await join_api.request_otp(mismatch, make_request())
		assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_contact_submit_is_limited_per_forwarded_ip(monkeypatch):
	sent = []

	async def fake_send_message_to_channel(**kwargs):
		sent.append(kwargs)
		return {"id": "message-id"}

	monkeypatch.setattr(contact_api, "DISCORD_BOT_TOKEN", "dummy-token")
	monkeypatch.setattr(contact_api, "send_message_to_channel", fake_send_message_to_channel)
	payload = contact_api.ContactRequest(email="sender@example.com", name="テスト 太郎", message="本文")

	for _ in range(CONTACT_RATE_LIMIT):
		await contact_api.submit_contact(payload, _forwarded_request())

	with pytest.raises(HTTPException) as error:
		await contact_api.submit_contact(payload, _forwarded_request())

	assert error.value.status_code == 429
	assert len(sent) == CONTACT_RATE_LIMIT
