"""Discord API の 429（レート制限）再試行のテスト（#170）

- 429 を受けたら retry_after（ボディ）または Retry-After（ヘッダー）の秒数だけ待って再試行する
- 再試行回数・待ち時間の上限を超える場合や待ち秒数が分からない場合は、待たずに失敗とする
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import DISCORD_RATE_LIMIT_MAX_RETRIES, DISCORD_RATE_LIMIT_MAX_WAIT
from app.services import discord_client

GUILD_ID = "guild-1"
USER_ID = "user-1"
ROLE_ID = "role-a"
REQUEST = httpx.Request("PUT", f"{discord_client.DISCORD_API_BASE}/guilds/{GUILD_ID}/members/{USER_ID}/roles/{ROLE_ID}")


def _rate_limited(retry_after: float | None = None, header: str | None = None, scope: str = "user") -> httpx.Response:
	headers = {"X-RateLimit-Scope": scope}
	if header is not None:
		headers["Retry-After"] = header
	if retry_after is None:
		return httpx.Response(429, headers=headers, text="rate limited", request=REQUEST)
	return httpx.Response(
		429,
		headers=headers,
		json={"message": "You are being rate limited.", "retry_after": retry_after, "global": scope == "global"},
		request=REQUEST,
	)


def _ok() -> httpx.Response:
	return httpx.Response(204, request=REQUEST)


@pytest.fixture
def mock_sleep():
	with patch.object(discord_client.asyncio, "sleep", new_callable=AsyncMock) as sleep:
		yield sleep


def _patch_put(responses: list[httpx.Response]):
	return patch("httpx.AsyncClient.put", new_callable=AsyncMock, side_effect=responses)


class TestRateLimitRetry:
	@pytest.mark.asyncio
	async def test_retries_after_retry_after_in_body(self, mock_sleep):
		with _patch_put([_rate_limited(retry_after=1.5), _ok()]) as mock_put:
			await discord_client.add_role_to_member(GUILD_ID, USER_ID, ROLE_ID, "token")

		assert mock_put.await_count == 2
		mock_sleep.assert_awaited_once_with(1.5)

	@pytest.mark.asyncio
	async def test_uses_retry_after_header_when_body_has_no_retry_after(self, mock_sleep):
		with _patch_put([_rate_limited(header="2"), _ok()]) as mock_put:
			await discord_client.add_role_to_member(GUILD_ID, USER_ID, ROLE_ID, "token")

		assert mock_put.await_count == 2
		mock_sleep.assert_awaited_once_with(2.0)

	@pytest.mark.asyncio
	async def test_global_scope_also_waits_retry_after(self, mock_sleep):
		with _patch_put([_rate_limited(retry_after=0.5, scope="global"), _ok()]) as mock_put:
			await discord_client.add_role_to_member(GUILD_ID, USER_ID, ROLE_ID, "token")

		assert mock_put.await_count == 2
		mock_sleep.assert_awaited_once_with(0.5)

	@pytest.mark.asyncio
	async def test_fails_after_max_retries(self, mock_sleep):
		responses = [_rate_limited(retry_after=0.1) for _ in range(DISCORD_RATE_LIMIT_MAX_RETRIES + 1)]
		with _patch_put(responses) as mock_put:
			with pytest.raises(httpx.HTTPStatusError) as exc_info:
				await discord_client.add_role_to_member(GUILD_ID, USER_ID, ROLE_ID, "token")

		assert exc_info.value.response.status_code == 429
		assert mock_put.await_count == 1 + DISCORD_RATE_LIMIT_MAX_RETRIES
		assert mock_sleep.await_count == DISCORD_RATE_LIMIT_MAX_RETRIES

	@pytest.mark.asyncio
	async def test_does_not_wait_when_retry_after_exceeds_max_wait(self, mock_sleep):
		with _patch_put([_rate_limited(retry_after=DISCORD_RATE_LIMIT_MAX_WAIT + 1), _ok()]) as mock_put:
			with pytest.raises(httpx.HTTPStatusError):
				await discord_client.add_role_to_member(GUILD_ID, USER_ID, ROLE_ID, "token")

		assert mock_put.await_count == 1
		mock_sleep.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_does_not_retry_when_wait_seconds_are_unknown(self, mock_sleep):
		with _patch_put([_rate_limited(), _ok()]) as mock_put:
			with pytest.raises(httpx.HTTPStatusError):
				await discord_client.add_role_to_member(GUILD_ID, USER_ID, ROLE_ID, "token")

		assert mock_put.await_count == 1
		mock_sleep.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_set_member_roles_retries_and_succeeds(self, mock_sleep):
		with patch("httpx.AsyncClient.patch", new_callable=AsyncMock, side_effect=[_rate_limited(retry_after=1.0), _ok()]) as mock_patch:
			await discord_client.set_member_roles(GUILD_ID, USER_ID, [ROLE_ID], "token")

		assert mock_patch.await_count == 2
		mock_sleep.assert_awaited_once_with(1.0)

	@pytest.mark.asyncio
	async def test_rate_limit_logs_do_not_contain_discord_ids(self, mock_sleep, caplog):
		guild_id = "100000000000000001"
		user_id = "200000000000000002"
		responses = [_rate_limited(retry_after=0.1) for _ in range(DISCORD_RATE_LIMIT_MAX_RETRIES + 1)]
		with patch("httpx.AsyncClient.patch", new_callable=AsyncMock, side_effect=responses):
			with caplog.at_level("WARNING", logger=discord_client.logger.name):
				with pytest.raises(discord_client.DiscordAPIError):
					await discord_client.set_member_roles(guild_id, user_id, [ROLE_ID], "token")

		assert "Discord rate limited" in caplog.text
		assert "/guilds/:id/members/:id" in caplog.text
		assert guild_id not in caplog.text
		assert user_id not in caplog.text


class TestClientReuse:
	@pytest.mark.asyncio
	async def test_uses_given_client_without_creating_new_one(self, mock_sleep):
		client = AsyncMock(spec=httpx.AsyncClient)
		client.patch.return_value = _ok()

		with patch("httpx.AsyncClient") as mock_client_cls:
			await discord_client.set_member_roles(GUILD_ID, USER_ID, [ROLE_ID], "token", client=client)
			await discord_client.set_member_roles(GUILD_ID, "user-2", [ROLE_ID], "token", client=client)

		mock_client_cls.assert_not_called()
		assert client.patch.await_count == 2
