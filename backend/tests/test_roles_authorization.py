"""ロール情報APIの認可境界を検証するテスト。"""

import inspect

from app.api.v1.roles import get_lists, get_my_role_assignments, get_role_members
from app.core.auth import require_admin, require_member


def test_full_role_member_list_requires_admin():
	dependency = inspect.signature(get_role_members).parameters["_principal"].default.dependency
	assert dependency is require_admin


def test_full_member_lists_requires_admin():
	dependency = inspect.signature(get_lists).parameters["_principal"].default.dependency
	assert dependency is require_admin


def test_my_assignments_is_member_scoped():
	dependency = inspect.signature(get_my_role_assignments).parameters["_principal"].default.dependency
	assert dependency is require_member