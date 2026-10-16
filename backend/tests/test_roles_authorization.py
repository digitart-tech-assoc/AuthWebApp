"""ロール情報APIの認可境界を検証するテスト。"""

import inspect
import re

import pytest
from fastapi import HTTPException

from app.api.v1.roles import get_lists, get_my_role_assignments, get_role_members
from app.core.auth import has_member_privilege, require_admin, require_member
from app.core.config import MEMBERSHIP_PRIORITY_SQL, MembershipType


def test_full_role_member_list_requires_admin():
	dependency = inspect.signature(get_role_members).parameters["_principal"].default.dependency
	assert dependency is require_admin


def test_full_member_lists_requires_admin():
	dependency = inspect.signature(get_lists).parameters["_principal"].default.dependency
	assert dependency is require_admin


def test_my_assignments_is_member_scoped():
	dependency = inspect.signature(get_my_role_assignments).parameters["_principal"].default.dependency
	assert dependency is require_member

@pytest.mark.parametrize("app_role", ["member", "sub_user", "obog", "admin"])
def test_member_privileged_roles_can_use_member_features(app_role):
	# obog / sub_user は member と同じ権限を持つ
	assert has_member_privilege(app_role) is True
	assert require_member({"app_role": app_role}) == {"app_role": app_role}


@pytest.mark.parametrize("app_role", ["pre_member", "none", None])
def test_non_member_roles_cannot_use_member_features(app_role):
	assert has_member_privilege(app_role) is False
	with pytest.raises(HTTPException) as exc_info:
		require_member({"app_role": app_role})
	assert exc_info.value.status_code == 403


@pytest.mark.parametrize("app_role", ["member", "sub_user", "obog"])
def test_member_privileged_roles_are_not_admin(app_role):
	with pytest.raises(HTTPException) as exc_info:
		require_admin({"app_role": app_role})
	assert exc_info.value.status_code == 403


def test_membership_priority_ranks_member_privileged_roles_between_admin_and_pre_member():
	# app_role の解決順位: admin > member / sub_user / obog > pre_member（同順位は作らない）
	ranks = {name: int(rank) for name, rank in re.findall(r"WHEN '(\w+)' THEN (\d+)", MEMBERSHIP_PRIORITY_SQL)}

	assert set(ranks) == set(MembershipType.ALL)
	assert len(set(ranks.values())) == len(ranks)
	privileged_ranks = [ranks[t] for t in MembershipType.MEMBER_PRIVILEGED]
	assert ranks[MembershipType.ADMIN] < min(privileged_ranks)
	assert max(privileged_ranks) < ranks[MembershipType.PRE_MEMBER]
