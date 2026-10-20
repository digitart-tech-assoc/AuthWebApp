"""レート制限のテスト（#82）

- 上限までは受け付け、超えたら次に受け付けられるまでの秒数を付けて拒否する
- 窓の外に出た記録は数えず、記録がなくなったキーは消す
- クライアント IP は X-Forwarded-For の最右端（ingress が付けた値）、なければ接続元を使う
"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.rate_limit import (
	RateLimitExceededError,
	SlidingWindowRateLimiter,
	enforce_rate_limit,
	get_client_ip,
)


class FakeClock:
	def __init__(self) -> None:
		self.now = 1000.0

	def __call__(self) -> float:
		return self.now


def _request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.1") -> Request:
	raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
	return Request({"type": "http", "headers": raw_headers, "client": (client_host, 12345)})


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
		request = _request({"X-Forwarded-For": "203.0.113.9, 198.51.100.7"})
		assert get_client_ip(request) == "198.51.100.7"

	def test_falls_back_to_client_host(self):
		assert get_client_ip(_request(client_host="192.0.2.1")) == "192.0.2.1"

	def test_ignores_empty_forwarded_for(self):
		assert get_client_ip(_request({"X-Forwarded-For": " , "}, client_host="192.0.2.1")) == "192.0.2.1"


@pytest.mark.asyncio
async def test_enforce_returns_429_without_logging_key(caplog):
	limiter = SlidingWindowRateLimiter(1, 600, clock=FakeClock())
	await enforce_rate_limit(limiter, "ip:203.0.113.9", "contact")

	with pytest.raises(HTTPException) as error:
		await enforce_rate_limit(limiter, "ip:203.0.113.9", "contact")

	assert error.value.status_code == 429
	assert error.value.headers == {"Retry-After": "600"}
	assert "endpoint=contact" in caplog.text
	assert "203.0.113.9" not in caplog.text
