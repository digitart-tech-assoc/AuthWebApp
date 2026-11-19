"""GET /api/v1/members/pre_member/list の Discord API 呼び出しのテスト"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.api.v1 import members as members_api


@pytest.mark.asyncio
async def test_waits_for_bucket_reset_when_fetching_each_member(monkeypatch):
	"""一覧の人数分、同じバケットへ続けて送るので、すべての取得で wait_for_bucket_reset=True を渡す。"""
	monkeypatch.setattr(members_api, "DISCORD_TOKEN", "token")
	monkeypatch.setattr(members_api, "DISCORD_GUILD_ID", "1")
	monkeypatch.setattr(
		members_api,
		"get_pre_member_list_with_users",
		lambda search: [{"discord_id": "100"}, {"discord_id": "200"}, {"discord_id": "300"}],
	)
	fetch = AsyncMock(return_value={"username": "name", "display_name": None})
	monkeypatch.setattr(members_api, "fetch_guild_member", fetch)

	response = await members_api.get_pre_member_list(search=None, _principal={})

	assert response["ok"] is True
	assert fetch.await_count == 3
	assert all(call.kwargs.get("wait_for_bucket_reset") is True for call in fetch.await_args_list)
