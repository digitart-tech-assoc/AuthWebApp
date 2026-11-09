"""Bot の内部同期 URL を、環境変数名によらず同じ値で解決することのテスト（#173）

Backend の push 後の reconcile 依頼（roles.py）と、本入会時のロール同期依頼（student.py）が、
`BOT_INTERNAL_URL` に設定した URL へ通知することを検証する。実際の通信は行わない。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1 import roles as roles_api
from app.api.v1 import student as student_api
from app.core.bot_url import get_bot_sync_endpoint

K8S_URL = "http://authwebapp-discord-bot-service:8000/internal/sync"


@pytest.fixture(autouse=True)
def _clear_bot_env(monkeypatch):
	monkeypatch.delenv("BOT_INTERNAL_URL", raising=False)
	monkeypatch.delenv("DISCORD_BOT_URL", raising=False)


def test_default_endpoint_when_unset():
	assert get_bot_sync_endpoint() == "http://discord-bot:8000/internal/sync"


@pytest.mark.parametrize(
	"value",
	[
		K8S_URL,
		K8S_URL + "/",
		"http://authwebapp-discord-bot-service:8000",
		"http://authwebapp-discord-bot-service:8000/",
	],
)
def test_bot_internal_url_is_normalized(monkeypatch, value):
	monkeypatch.setenv("BOT_INTERNAL_URL", value)
	assert get_bot_sync_endpoint() == K8S_URL


def test_legacy_name_is_used_only_when_new_name_is_unset(monkeypatch):
	monkeypatch.setenv("DISCORD_BOT_URL", "http://legacy:8000")
	assert get_bot_sync_endpoint() == "http://legacy:8000/internal/sync"
	monkeypatch.setenv("BOT_INTERNAL_URL", K8S_URL)
	assert get_bot_sync_endpoint() == K8S_URL


def _fake_client(status_code: int = 200):
	response = MagicMock(status_code=status_code, text="")
	response.json.return_value = {"result": {"added": 0, "removed": 0, "errors": []}}
	client = MagicMock()
	client.post = AsyncMock(return_value=response)
	ctx = MagicMock()
	ctx.__aenter__ = AsyncMock(return_value=client)
	ctx.__aexit__ = AsyncMock(return_value=False)
	return client, ctx


@pytest.mark.asyncio
async def test_push_reconcile_posts_to_bot_internal_url(monkeypatch):
	monkeypatch.setenv("BOT_INTERNAL_URL", K8S_URL)
	client, ctx = _fake_client()
	with patch.object(roles_api.httpx, "AsyncClient", return_value=ctx):
		assert await roles_api._notify_bot_to_reconcile() is True
	assert client.post.await_args.args[0] == K8S_URL


@pytest.mark.asyncio
async def test_student_sync_posts_to_bot_internal_url(monkeypatch):
	monkeypatch.setenv("BOT_INTERNAL_URL", K8S_URL)
	client, ctx = _fake_client()
	with patch.object(student_api.httpx, "AsyncClient", return_value=ctx):
		assert await student_api._notify_discord_bot_sync("123456789012345678") is True
	assert client.post.await_args.args[0] == K8S_URL
