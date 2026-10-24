"""audit_repository（監査ログの共通処理）のテスト"""

import asyncio
import json
import logging

import pytest

from app.db import audit_repository
from app.db.audit_repository import (
	AuditContext,
	AuditLog,
	assignment_diff,
	diff_fields,
	get_audit_context,
	insert_audit_logs,
	internal_audit_context,
	record_discord_audit_safely,
)

ROLE_FIELDS = ("name", "color", "permissions")
AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="111", operation="manifest_patch")


class _RecordingCursor:
	def __init__(self):
		self.executed = []

	def execute(self, sql, params=None):
		self.executed.append((" ".join(sql.split()), params))


def test_diff_fields_returns_only_changed_fields():
	before = {"name": "advisor", "color": "#000000", "permissions": 8}
	after = {"name": "advisor", "color": "#000000", "permissions": 0}

	assert diff_fields(before, after, ROLE_FIELDS) == ({"permissions": 8}, {"permissions": 0})


def test_diff_fields_returns_none_when_nothing_changed():
	row = {"name": "advisor", "color": "#000000", "permissions": 8}

	assert diff_fields(row, dict(row), ROLE_FIELDS) is None


def test_diff_fields_compares_permissions_as_int():
	assert diff_fields({"permissions": "8"}, {"permissions": 8}, ("permissions",)) is None
	assert diff_fields({"permissions": "8"}, {"permissions": 0}, ("permissions",)) == ({"permissions": 8}, {"permissions": 0})


def test_diff_fields_records_color_case_change_as_is():
	assert diff_fields({"color": "#99AAB5"}, {"color": "#99aab5"}, ("color",)) == (
		{"color": "#99AAB5"},
		{"color": "#99aab5"},
	)


def test_diff_fields_create_and_delete_use_null_on_one_side():
	row = {"name": "advisor", "color": "#000000", "permissions": 8}

	assert diff_fields(None, row, ROLE_FIELDS) == (None, row)
	assert diff_fields(row, None, ROLE_FIELDS) == (row, None)
	assert diff_fields(None, None, ROLE_FIELDS) is None


def test_assignment_diff_sorts_and_skips_empty():
	assert assignment_diff({"2", "1"}, []) == {"added": ["1", "2"], "removed": []}
	assert assignment_diff([], []) is None


def test_insert_audit_logs_writes_context_and_json():
	cur = _RecordingCursor()
	log = AuditLog("db", "role", "r1", "update", {"permissions": 8}, {"permissions": 0})

	insert_audit_logs(cur, AUDIT, [log])

	assert len(cur.executed) == 1
	sql, params = cur.executed[0]
	assert sql.startswith("INSERT INTO role_audit_logs")
	assert params == (
		"req-1", "manifest_patch", "db", "role", "r1", "update",
		json.dumps({"permissions": 8}), json.dumps({"permissions": 0}), "sub-1", "111",
	)


def test_insert_audit_logs_does_nothing_without_context_or_logs():
	cur = _RecordingCursor()

	insert_audit_logs(cur, None, [AuditLog("db", "role", "r1", "update")])
	insert_audit_logs(cur, AUDIT, [])

	assert cur.executed == []


def test_insert_audit_logs_logs_summary_with_request_id(caplog):
	caplog.set_level(logging.INFO, logger=audit_repository.__name__)

	insert_audit_logs(_RecordingCursor(), AUDIT, [AuditLog("db", "role", "r1", "update", {"name": "a"}, {"name": "b"})])

	assert "request_id=req-1" in caplog.text
	assert "rows=1" in caplog.text
	# 要約にはロール定義の値を出さない
	assert "\"name\"" not in caplog.text


def test_record_discord_audit_safely_swallows_errors(monkeypatch, caplog):
	def _fail(audit, logs):
		raise RuntimeError("Key (name)=(secret) violates constraint")

	monkeypatch.setattr(audit_repository, "record_audit_logs", _fail)
	caplog.set_level(logging.ERROR, logger=audit_repository.__name__)

	asyncio.run(record_discord_audit_safely(AUDIT, [AuditLog("discord", "role", "r1", "update")]))

	assert "Failed to record role audit logs" in caplog.text
	assert "RuntimeError" in caplog.text
	assert "secret" not in caplog.text


def test_record_discord_audit_safely_writes_logs(monkeypatch):
	calls = []
	monkeypatch.setattr(audit_repository, "record_audit_logs", lambda audit, logs: calls.append((audit, logs)))
	log = AuditLog("discord", "role", "r1", "update")

	asyncio.run(record_discord_audit_safely(AUDIT, [log]))

	assert calls == [(AUDIT, [log])]


def test_get_audit_context_uses_principal_and_new_request_id():
	principal = {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}

	first = get_audit_context(principal)
	second = get_audit_context(principal)

	assert first.actor_sub == "sub-1"
	assert first.actor_discord_id == "111"
	assert first.request_id != second.request_id


def test_internal_audit_context_has_no_discord_id():
	ctx = internal_audit_context("pre_member_register")

	assert ctx.actor_sub == "internal-service"
	assert ctx.actor_discord_id is None
	assert ctx.operation == "pre_member_register"


def test_with_operation_keeps_request_id():
	ctx = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id=None)

	assert ctx.with_operation("push") == AuditContext("req-1", "sub-1", None, "push")


@pytest.mark.parametrize("value", [None, "8"])
def test_diff_fields_keeps_null_permissions(value):
	result = diff_fields({"permissions": value}, None, ("permissions",))
	assert result == ({"permissions": None if value is None else 8}, None)
