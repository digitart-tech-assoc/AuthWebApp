"""セルフロール一括更新時の Discord API 呼び出しの最適化のテスト（#115）

- Bot 自身のユーザー ID（GET /users/@me）をキャッシュし、2 回目以降は呼ばない
- ロール一覧とメンバー情報を並列に取得する
- 並列化してもエラーの優先順位（ロール取得失敗 → 検証 → メンバー取得失敗）は変わらない
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import roles as roles_api
from app.services import discord_client

PRINCIPAL = {"discord_id": "user-456", "app_role": "member"}
MANIFEST = {
	"roles": [{"role_id": "role-x", "name": "X", "category_id": "cat-open", "permissions": 0}],
	"categories": [{"id": "cat-open", "name": "趣味", "is_restricted": False}],
}
DISCORD_ROLES = [
	{"role_id": "role-x", "position": 1, "managed": False},
	{"role_id": "role-bot", "position": 10, "managed": True, "is_our_bot": True},
]


def _response(json_data) -> MagicMock:
	response = MagicMock()
	response.json.return_value = json_data
	response.raise_for_status.return_value = None
	return response


class TestBotUserIdCache:
	@pytest.fixture(autouse=True)
	def clear_cache(self):
		discord_client._bot_user_id_cache.clear()
		yield
		discord_client._bot_user_id_cache.clear()

	@pytest.mark.asyncio
	async def test_users_me_is_requested_only_once(self):
		requested_urls = []

		async def fake_get(self, url, **kwargs):
			requested_urls.append(url)
			if url.endswith("/users/@me"):
				return _response({"id": "bot-id"})
			return _response([{"id": "role-bot", "name": "Bot", "position": 10, "managed": True, "tags": {"bot_id": "bot-id"}}])

		with patch("httpx.AsyncClient.get", new=fake_get):
			first = await discord_client.fetch_guild_roles("guild-123", "bot-token")
			second = await discord_client.fetch_guild_roles("guild-123", "bot-token")

		assert first[0]["is_our_bot"] is True
		assert second[0]["is_our_bot"] is True
		assert sum(url.endswith("/users/@me") for url in requested_urls) == 1
		assert sum(url.endswith("/guilds/guild-123/roles") for url in requested_urls) == 2


class TestSelfBatchDiscordFetch:
	@pytest.fixture(autouse=True)
	def common_patches(self):
		with patch.object(roles_api, "_get_token", return_value="token"), \
			patch.object(roles_api, "fetch_manifest", return_value=MANIFEST), \
			patch.object(roles_api, "batch_update_user_roles"):
			yield

	@pytest.mark.asyncio
	async def test_fetches_roles_and_member_concurrently(self):
		roles_started = asyncio.Event()
		member_started = asyncio.Event()

		# 互いの開始を待つ。直列に呼ぶと先に呼んだ側が待ち続けてタイムアウトする
		async def fake_fetch_roles(*args):
			roles_started.set()
			await asyncio.wait_for(member_started.wait(), timeout=1)
			return DISCORD_ROLES

		async def fake_fetch_member(*args):
			member_started.set()
			await asyncio.wait_for(roles_started.wait(), timeout=1)
			return {"role_ids": []}

		with patch.object(roles_api, "fetch_guild_roles", new=fake_fetch_roles), \
			patch.object(roles_api, "fetch_guild_member", new=fake_fetch_member), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			result = await roles_api.self_batch_roles(
				roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL
			)

		assert result["ok"] is True
		assert result["added"] == ["role-x"]
		mock_set.assert_awaited_once()

	@pytest.mark.asyncio
	async def test_returns_502_when_role_fetch_fails(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, side_effect=Exception("roles down")), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": []}), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL)

		assert error.value.status_code == 502
		assert "fetch roles" in error.value.detail
		mock_set.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_returns_502_when_member_fetch_fails(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, side_effect=Exception("member down")), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL)

		assert error.value.status_code == 502
		assert "fetch member" in error.value.detail
		mock_set.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_validation_error_takes_precedence_over_member_fetch_failure(self):
		# Bot より上位のロールは、メンバー取得が失敗していても従来どおり 403 で拒否する
		discord_roles = [
			{"role_id": "role-x", "position": 20, "managed": False},
			{"role_id": "role-bot", "position": 10, "managed": True, "is_our_bot": True},
		]
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=discord_roles), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, side_effect=Exception("member down")), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL)

		assert error.value.status_code == 403
		mock_set.assert_not_awaited()
