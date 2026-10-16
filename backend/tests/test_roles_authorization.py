"""ロール情報APIの認可境界およびメンバーリスト同期レスポンスを検証するテスト。"""

import inspect
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.roles as roles_api
from app.api.v1.roles import get_lists, get_my_role_assignments, get_role_members, sync_members_from_discord
from app.core.auth import has_member_privilege, require_admin, require_member


def test_full_role_member_list_requires_admin():
	dependency = inspect.signature(get_role_members).parameters["_principal"].default.dependency
	assert dependency is require_admin


def test_full_member_lists_requires_admin():
	dependency = inspect.signature(get_lists).parameters["_principal"].default.dependency
	assert dependency is require_admin


def test_my_assignments_is_member_scoped():
	dependency = inspect.signature(get_my_role_assignments).parameters["_principal"].default.dependency
	assert dependency is require_member


@pytest.mark.parametrize("role", ["member", "sub_user", "obog", "admin"])
def test_require_member_allows_privileged_roles(role: str):
	assert has_member_privilege(role) is True
	principal = {"sub": "user-1", "app_role": role}
	assert require_member(principal) == principal


@pytest.mark.parametrize("role", ["pre_member", "none", None, ""])
def test_require_member_rejects_non_privileged_roles(role: str | None):
	assert has_member_privilege(role) is False
	with pytest.raises(HTTPException) as exc_info:
		require_member({"sub": "user-1", "app_role": role})
	assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_sync_members_from_discord_returns_all_five_lists(monkeypatch):
	monkeypatch.setattr(roles_api, "_get_token", lambda: "dummy-token")
	monkeypatch.setattr(roles_api, "DISCORD_GUILD_ID", "guild-1")
	monkeypatch.setattr(
		roles_api,
		"fetch_guild_roles",
		AsyncMock(return_value=[{"role_id": "r-member", "name": "member"}, {"role_id": "r-obog", "name": "OBOG"}]),
	)
	monkeypatch.setattr(
		roles_api,
		"fetch_all_guild_members",
		AsyncMock(return_value=[{"user_id": "u-1", "username": "user1", "role_ids": ["r-member"]}]),
	)
	monkeypatch.setattr(roles_api, "save_guild_members", lambda members: None)
	expected_sync = {
		"member_list": [{"discord_id": "u-1", "assigned_at": None}],
		"sub_user_list": [{"discord_id": "u-2", "assigned_at": None}],
		"admin_list": [{"discord_id": "u-3", "assigned_at": None}],
		"pre_member_list": [{"discord_id": "u-4", "assigned_at": None}],
		"obog_list": [{"discord_id": "u-5", "assigned_at": None}],
	}
	monkeypatch.setattr(roles_api, "sync_member_lists", lambda *args, **kwargs: expected_sync)

	res = await sync_members_from_discord(_principal={"app_role": "admin"})
	assert res == {
		"ok": True,
		"guild_id": "guild-1",
		**expected_sync,
	}