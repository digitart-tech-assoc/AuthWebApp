"""内部連携向け GET /api/v1/auth/role-by-sub のテスト（#205）"""

import pytest
from fastapi import HTTPException

import app.api.v1.users as users_api

INTERNAL_PRINCIPAL = {"auth_type": "internal", "sub": "internal-service", "app_role": "admin"}
SUB = "00000000-0000-0000-0000-000000000001"
DISCORD_ID = "100000000000000001"


def _patch_user(monkeypatch, *, role: str, is_paid: bool = False) -> list[str]:
	"""ユーザー取得・ロール解決・支払い状態をモックし、支払い状態を照会した Discord ID を記録する。"""
	paid_checks: list[str] = []
	monkeypatch.setattr(
		users_api,
		"find_user_by_sub",
		lambda sub: {"id": 1, "user_id": sub, "discord_id": DISCORD_ID, "created_at": None, "updated_at": None},
	)
	monkeypatch.setattr(users_api, "get_user_role", lambda sub: role)
	monkeypatch.setattr(users_api, "is_paid_invitation", lambda discord_id: paid_checks.append(discord_id) or is_paid)
	return paid_checks


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "member", "sub_user", "obog", "pre_member"])
async def test_returns_role_resolved_from_memberships(monkeypatch, role):
	paid_checks = _patch_user(monkeypatch, role=role)

	res = await users_api.get_role_by_sub(sub=SUB, principal=INTERNAL_PRINCIPAL)

	assert res.app_role == role
	assert res.discord_id == DISCORD_ID
	assert res.is_paid is False
	# ロールを持つユーザーは支払い状態を照会しない
	assert paid_checks == []


@pytest.mark.asyncio
async def test_checks_paid_invitation_only_for_user_without_role(monkeypatch):
	paid_checks = _patch_user(monkeypatch, role="none", is_paid=True)

	res = await users_api.get_role_by_sub(sub=SUB, principal=INTERNAL_PRINCIPAL)

	assert res.app_role == "none"
	assert res.is_paid is True
	assert paid_checks == [DISCORD_ID]


@pytest.mark.asyncio
async def test_returns_none_for_unknown_sub(monkeypatch):
	monkeypatch.setattr(users_api, "find_user_by_sub", lambda sub: None)

	res = await users_api.get_role_by_sub(sub=SUB, principal=INTERNAL_PRINCIPAL)

	assert res.app_role == "none"
	assert res.discord_id is None
	assert res.is_paid is False


@pytest.mark.asyncio
async def test_rejects_non_internal_principal():
	with pytest.raises(HTTPException) as exc_info:
		await users_api.get_role_by_sub(sub=SUB, principal={"auth_type": "user", "app_role": "admin"})
	assert exc_info.value.status_code == 403
