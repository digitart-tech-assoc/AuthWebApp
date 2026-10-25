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
from tests.request_factory import TEST_AUDIT

PRINCIPAL = {"discord_id": "user-456", "app_role": "member"}
MANIFEST = {
	"roles": [{"role_id": "role-x", "name": "X", "category_id": "cat-open", "permissions": 0}],
	"categories": [{"id": "cat-open", "name": "趣味", "is_restricted": False}],
}
DISCORD_ROLES = [
	{"role_id": "role-x", "position": 1, "managed": False},
	{"role_id": "role-bot", "position": 10, "managed": True, "is_our_bot": True},
]
BOT_MEMBER = {"role_ids": ["role-bot"]}


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
			if url.endswith("/guilds/guild-123/roles"):
				return _response([{"id": "role-bot", "name": "Bot", "position": 10, "managed": True, "tags": {"bot_id": "bot-id"}}])
			return _response({
				"user": {"id": "bot-id", "username": "bot"},
				"roles": ["role-bot"],
			})

		with patch("httpx.AsyncClient.get", new=fake_get):
			first = await discord_client.fetch_guild_roles("guild-123", "bot-token")
			second = await discord_client.fetch_guild_roles("guild-123", "bot-token")
			member = await discord_client.fetch_bot_guild_member("guild-123", "bot-token")

		assert first[0]["is_our_bot"] is True
		assert second[0]["is_our_bot"] is True
		assert member["role_ids"] == ["role-bot"]
		assert sum(url.endswith("/users/@me") for url in requested_urls) == 1
		assert sum(url.endswith("/guilds/guild-123/roles") for url in requested_urls) == 2
		assert sum("/guilds/guild-123/members/" in url for url in requested_urls) == 1


class TestChannelPermissionOverwrites:
	@pytest.mark.asyncio
	async def test_returns_role_overwrites_that_allow_permissions(self):
		response = _response([
			{"permission_overwrites": [
				{"id": "role-allowed", "type": 0, "allow": "1024", "deny": "0"},
				{"id": "role-denied", "type": 0, "allow": "0", "deny": "1024"},
				{"id": "member-allowed", "type": 1, "allow": "1024", "deny": "0"},
			]},
			{"permission_overwrites": [
				{"id": "role-allowed", "type": 0, "allow": "2048", "deny": "0"},
			]},
		])
		requests = []

		async def fake_request(client, method, url, **kwargs):
			requests.append((method, url, kwargs["headers"]))
			return response

		with patch.object(discord_client, "_request", new=fake_request):
			role_ids = await discord_client.fetch_role_ids_with_channel_permissions("guild-123", "token")

		assert role_ids == {"role-allowed"}
		assert requests == [(
			"GET",
			f"{discord_client.DISCORD_API_BASE}/guilds/guild-123/channels",
			{"Authorization": "Bot token", "Content-Type": "application/json"},
		)]


class TestSelfBatchDiscordFetch:
	@pytest.fixture(autouse=True)
	def common_patches(self):
		with patch.object(roles_api, "_get_token", return_value="token"), \
			patch.object(roles_api, "fetch_manifest", return_value=MANIFEST), \
			patch.object(roles_api, "batch_update_user_roles"), \
			patch.object(roles_api, "fetch_bot_guild_member", new_callable=AsyncMock, return_value=BOT_MEMBER), \
			patch.object(roles_api, "fetch_role_ids_with_channel_permissions", new_callable=AsyncMock, return_value=set()):
			yield

	@pytest.mark.asyncio
	async def test_fetches_roles_member_and_channel_overwrites_concurrently(self):
		roles_started = asyncio.Event()
		member_started = asyncio.Event()
		bot_member_started = asyncio.Event()
		channel_overwrites_started = asyncio.Event()

		# 互いの開始を待つ。直列に呼ぶと先に呼んだ側が待ち続けてタイムアウトする
		async def fake_fetch_roles(*args):
			roles_started.set()
			await asyncio.wait_for(member_started.wait(), timeout=1)
			await asyncio.wait_for(bot_member_started.wait(), timeout=1)
			await asyncio.wait_for(channel_overwrites_started.wait(), timeout=1)
			return DISCORD_ROLES

		async def fake_fetch_member(*args):
			member_started.set()
			await asyncio.wait_for(roles_started.wait(), timeout=1)
			await asyncio.wait_for(bot_member_started.wait(), timeout=1)
			await asyncio.wait_for(channel_overwrites_started.wait(), timeout=1)
			return {"role_ids": []}

		async def fake_fetch_bot_member(*args):
			bot_member_started.set()
			await asyncio.wait_for(roles_started.wait(), timeout=1)
			await asyncio.wait_for(member_started.wait(), timeout=1)
			await asyncio.wait_for(channel_overwrites_started.wait(), timeout=1)
			return BOT_MEMBER

		async def fake_fetch_channel_overwrites(*args):
			channel_overwrites_started.set()
			await asyncio.wait_for(roles_started.wait(), timeout=1)
			await asyncio.wait_for(member_started.wait(), timeout=1)
			await asyncio.wait_for(bot_member_started.wait(), timeout=1)
			return set()

		with patch.object(roles_api, "fetch_guild_roles", new=fake_fetch_roles), \
			patch.object(roles_api, "fetch_guild_member", new=fake_fetch_member), \
			patch.object(roles_api, "fetch_bot_guild_member", new=fake_fetch_bot_member), \
			patch.object(roles_api, "fetch_role_ids_with_channel_permissions", new=fake_fetch_channel_overwrites), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			result = await roles_api.self_batch_roles(
				roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT
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
				await roles_api.self_batch_roles(roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT)

		assert error.value.status_code == 502
		assert "fetch roles" in error.value.detail
		mock_set.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_returns_502_when_member_fetch_fails(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, side_effect=Exception("member down")), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT)

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
				await roles_api.self_batch_roles(roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT)

		assert error.value.status_code == 403
		mock_set.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_rejects_adding_role_with_channel_permission_overwrite(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": []}), \
			patch.object(roles_api, "fetch_role_ids_with_channel_permissions", new_callable=AsyncMock, return_value={"role-x"}), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(
					roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT,
				)

		assert error.value.status_code == 403
		assert "チャンネル権限上書き" in error.value.detail
		mock_set.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_allows_removing_role_with_channel_permission_overwrite(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": ["role-x"]}), \
			patch.object(roles_api, "fetch_role_ids_with_channel_permissions", new_callable=AsyncMock) as mock_fetch_overwrites, \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			result = await roles_api.self_batch_roles(
				roles_api.SelfBatchPayload(roles_to_remove=["role-x"]), PRINCIPAL, audit=TEST_AUDIT,
			)

		assert result["ok"] is True
		mock_fetch_overwrites.assert_not_awaited()
		mock_set.assert_awaited_once()

	@pytest.mark.asyncio
	async def test_returns_502_when_channel_overwrite_fetch_fails(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": []}), \
			patch.object(
				roles_api, "fetch_role_ids_with_channel_permissions",
				new_callable=AsyncMock, side_effect=Exception("channels down"),
			), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(
					roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT,
				)

		assert error.value.status_code == 502
		assert "fetch channel permission overwrites" in error.value.detail
		mock_set.assert_not_awaited()

	@pytest.mark.asyncio
	async def test_uses_highest_role_assigned_to_bot_not_its_integration_role(self):
		discord_roles = [
			{"role_id": "role-x", "position": 15, "managed": False},
			{"role_id": "role-bot", "position": 10, "managed": True, "is_our_bot": True},
			{"role_id": "role-admin", "position": 20, "managed": False},
		]
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=discord_roles), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": []}), \
			patch.object(
				roles_api, "fetch_bot_guild_member", new_callable=AsyncMock,
				return_value={"role_ids": ["role-bot", "role-admin"]},
			), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			result = await roles_api.self_batch_roles(
				roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT
			)

		assert result["ok"] is True
		mock_set.assert_awaited_once()

	@pytest.mark.asyncio
	async def test_rejects_role_when_bot_top_role_cannot_be_identified(self):
		with patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": []}), \
			patch.object(roles_api, "fetch_bot_guild_member", new_callable=AsyncMock, return_value=None), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			with pytest.raises(HTTPException) as error:
				await roles_api.self_batch_roles(
					roles_api.SelfBatchPayload(roles_to_add=["role-x"]), PRINCIPAL, audit=TEST_AUDIT
				)

		assert error.value.status_code == 403
		mock_set.assert_not_awaited()
