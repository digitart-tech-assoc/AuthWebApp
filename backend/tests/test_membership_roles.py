"""会員種別のロール ID の設定と起動時の検証のテスト（#234）

- カンマ区切りの ID を、空要素と重複を除いて読む
- 本番では必須の種別（admin / member / pre_member）の ID が未設定なら起動しない
- 本番以外では警告のみで起動する
- 任意の種別（obog / sub_user）が未設定なら警告のみ
- メッセージにロール ID の値を含めない
"""

from __future__ import annotations

import logging

import pytest

from app.core import membership_roles
from app.core.config import MembershipType

REQUIRED_ENV = {
	"ADMIN_ROLE_IDS": "111111111111111111",
	"MEMBER_ROLE_IDS": "222222222222222222",
	"PRE_MEMBER_ROLE_ID": "333333333333333333",
}
OPTIONAL_ENV = {
	"OBOG_ROLE_IDS": "444444444444444444",
	"SUB_USER_ROLE_IDS": "555555555555555555",
}


@pytest.fixture
def role_env(monkeypatch):
	"""全種別のロール ID を設定する。"""
	for name, value in {**REQUIRED_ENV, **OPTIONAL_ENV}.items():
		monkeypatch.setenv(name, value)


def test_parses_comma_separated_ids(monkeypatch, role_env):
	monkeypatch.setenv("MEMBER_ROLE_IDS", " 1, 2,,1 ,3 ")

	ids = membership_roles.membership_role_ids()

	assert ids[MembershipType.MEMBER] == ("1", "2", "3")
	assert ids[MembershipType.ADMIN] == (REQUIRED_ENV["ADMIN_ROLE_IDS"],)


def test_unset_types_are_empty(monkeypatch, role_env):
	monkeypatch.delenv("OBOG_ROLE_IDS")

	assert membership_roles.membership_role_ids()[MembershipType.OBOG] == ()


def test_production_accepts_all_required_ids(role_env):
	membership_roles.validate_membership_role_ids("production")


@pytest.mark.parametrize("env_var", sorted(REQUIRED_ENV))
@pytest.mark.parametrize("value", [None, "", " , "])
def test_production_rejects_missing_required_ids(monkeypatch, role_env, env_var, value):
	if value is None:
		monkeypatch.delenv(env_var)
	else:
		monkeypatch.setenv(env_var, value)

	with pytest.raises(RuntimeError) as exc_info:
		membership_roles.validate_membership_role_ids("production")

	message = str(exc_info.value)
	assert env_var in message
	for configured in REQUIRED_ENV.values():
		assert configured not in message


@pytest.mark.parametrize("env", ["development", "local", ""])
def test_non_production_only_warns_for_missing_required_ids(monkeypatch, caplog, role_env, env):
	monkeypatch.delenv("ADMIN_ROLE_IDS")

	with caplog.at_level(logging.WARNING, logger=membership_roles.__name__):
		membership_roles.validate_membership_role_ids(env)

	assert "ADMIN_ROLE_IDS" in caplog.text


@pytest.mark.parametrize("env_var", sorted(OPTIONAL_ENV))
def test_missing_optional_ids_only_warn_in_production(monkeypatch, caplog, role_env, env_var):
	monkeypatch.delenv(env_var)

	with caplog.at_level(logging.WARNING, logger=membership_roles.__name__):
		membership_roles.validate_membership_role_ids("production")

	assert env_var in caplog.text


def test_does_not_warn_when_all_ids_are_set(caplog, role_env):
	with caplog.at_level(logging.WARNING, logger=membership_roles.__name__):
		membership_roles.validate_membership_role_ids("production")

	assert caplog.text == ""
