"""upsert_student_profile_and_promote のトランザクション内資格検証と、本会員化時の割当の更新のテスト"""

import pytest

from app.core.exceptions import RegistrationNotEligibleError
from app.db import student_repository
from app.db.audit_repository import AuditContext


class _FakeCursor:
	def __init__(self, conn):
		self._conn = conn
		self._result = None
		# psycopg2 のカーソルと同じく、直前の文で変わった行数を持つ
		# （INSERT は常に1行追加、DELETE は常に1行削除、pre_member の行の DELETE は pre_member のときだけ1行削除したとみなす）
		self.rowcount = 0

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def execute(self, sql, params=None):
		normalized = " ".join(sql.split())
		self._conn.executed.append(normalized)
		if normalized.startswith("DELETE FROM user_memberships"):
			# pre_member の行の DELETE ... RETURNING assigned_by
			self.rowcount = 1 if self._conn.is_pre_member else 0
		elif normalized.startswith(("INSERT", "DELETE")):
			self.rowcount = 1
		else:
			self.rowcount = 0
		self._conn.params.append(params)
		if normalized.startswith("DELETE FROM user_memberships"):
			self._result = ("S",) if self._conn.is_pre_member else None
		elif "FROM user_memberships" in normalized and normalized.startswith("SELECT"):
			self._result = (1,) if self._conn.is_pre_member else None
		elif "FROM paid_invitations" in normalized:
			self._result = (1,) if self._conn.is_paid else None
		else:
			self._result = None

	def fetchone(self):
		return self._result


class _FakeConnection:
	def __init__(self, is_pre_member: bool, is_paid: bool):
		self.is_pre_member = is_pre_member
		self.is_paid = is_paid
		self.executed: list[str] = []
		self.params: list = []
		self.committed = False
		self.rolled_back = False

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		# _PooledConnection と同様に例外時はロールバックする
		if exc_type is not None:
			self.rolled_back = True
		return False

	def cursor(self):
		return _FakeCursor(self)

	def commit(self):
		self.committed = True


def _promote(require_eligibility: bool = True, audit: AuditContext | None = None) -> student_repository.PromotionResult:
	return student_repository.upsert_student_profile_and_promote(
		profile_id="prof_test",
		discord_id="test-discord-id",
		student_number="1A234567",
		name="テスト 太郎",
		furigana="テスト タロウ",
		department="テスト学部",
		gender=None,
		phone="09000000000",
		email_aoyama="aa234567@aoyama.ac.jp",
		member_role_ids=["member-role"],
		require_eligibility=require_eligibility,
		audit=audit,
		pre_member_role_id="pre-member-role",
	)


def _writes(conn: _FakeConnection) -> list[str]:
	return [sql for sql in conn.executed if not sql.startswith("SELECT")]


@pytest.mark.parametrize(
	("is_pre_member", "is_paid", "detail"),
	[
		pytest.param(False, True, "入会予定者リストに登録されていません", id="not-pre-member"),
		pytest.param(True, False, "入会費の支払いが確認できません", id="not-paid"),
	],
)
def test_promotion_rejects_ineligible_user_without_writes(monkeypatch, is_pre_member, is_paid, detail):
	conn = _FakeConnection(is_pre_member=is_pre_member, is_paid=is_paid)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	with pytest.raises(RegistrationNotEligibleError) as error:
		_promote()

	assert str(error.value) == detail
	assert _writes(conn) == []
	assert conn.rolled_back
	assert not conn.committed


def test_promotion_locks_eligibility_rows_before_writes(monkeypatch):
	conn = _FakeConnection(is_pre_member=True, is_paid=True)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	assert _promote() == ("prof_test", True)

	assert "FOR UPDATE" in conn.executed[0] and "membership_type = 'pre_member'" in conn.executed[0]
	assert "FOR SHARE" in conn.executed[1] and "expires_at > now()" in conn.executed[1]
	assert any("DELETE FROM user_memberships" in sql for sql in _writes(conn))
	assert any("INSERT INTO user_memberships" in sql and "'member'" in sql for sql in _writes(conn))
	assert conn.committed


def test_promotion_skips_eligibility_check_for_registered_user(monkeypatch):
	conn = _FakeConnection(is_pre_member=False, is_paid=False)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	assert _promote(require_eligibility=False) == ("prof_test", False)

	assert not any("FROM paid_invitations" in sql for sql in conn.executed)
	assert conn.committed


def test_registered_user_update_does_not_change_role_assignments(monkeypatch):
	# 登録済みの会員（sub_user・obog など）のプロフィール更新では、種別も割当も変えない（#251）。
	# pre_member の行が残っていても member にしない
	conn = _FakeConnection(is_pre_member=True, is_paid=False)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	result = _promote(require_eligibility=False, audit=AuditContext("req-1", "sub-1", "test-discord-id", "student_profile"))

	assert result == ("prof_test", False)
	assert not any("user_memberships" in sql for sql in _writes(conn))
	assert not any("role_member_assignments" in sql for sql in conn.executed)
	assert not any("role_audit_logs" in sql for sql in conn.executed)


def test_promotion_adds_member_and_removes_pre_member_assignment(monkeypatch):
	# 割当の更新は本会員化（pre_member → member）と同じトランザクションで行う（#251）
	conn = _FakeConnection(is_pre_member=True, is_paid=True)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	assert _promote() == ("prof_test", True)

	writes = list(zip(conn.executed, conn.params))
	writes = [(sql, params) for sql, params in writes if not sql.startswith("SELECT")]
	sqls = [sql for sql, _ in writes]
	pre_delete = next(i for i, sql in enumerate(sqls) if sql.startswith("DELETE FROM user_memberships"))
	# member の行は、pre_member の行の assigned_by を引き継いで作る（すでにあれば何もしない）
	assert sqls[pre_delete + 1].startswith("INSERT INTO user_memberships") and "ON CONFLICT" in sqls[pre_delete + 1]
	assert writes[pre_delete + 1][1] == ("test-discord-id", "S")
	assert writes[pre_delete + 2] == (
		"INSERT INTO role_member_assignments (role_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
		("member-role", "test-discord-id"),
	)
	assert writes[pre_delete + 3] == (
		"DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s",
		("pre-member-role", "test-discord-id"),
	)
	assert conn.committed


def test_promotion_without_pre_member_role_id_keeps_other_assignments(monkeypatch):
	conn = _FakeConnection(is_pre_member=True, is_paid=True)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	student_repository.upsert_student_profile_and_promote(
		profile_id="prof_test", discord_id="test-discord-id", student_number="1A234567", name="テスト 太郎",
		furigana="テスト タロウ", department="テスト学部", gender=None, phone="09000000000",
		email_aoyama="aa234567@aoyama.ac.jp", member_role_ids=["member-role"], pre_member_role_id=None,
	)

	assert not any(sql.startswith("DELETE FROM role_member_assignments") for sql in conn.executed)


def test_promotion_records_role_assignment_in_same_transaction(monkeypatch):
	conn = _FakeConnection(is_pre_member=True, is_paid=True)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	_promote(audit=AuditContext("req-1", "sub-1", "test-discord-id", "student_profile"))

	writes = _writes(conn)
	assignment_index = next(i for i, sql in enumerate(writes) if sql.startswith("DELETE FROM role_member_assignments"))
	assert writes[assignment_index + 1].startswith("INSERT INTO role_audit_logs")
	audit_params = conn.params[conn.executed.index(writes[assignment_index + 1])]
	assert audit_params[3:6] == ("member_roles", "test-discord-id", "update")
	assert audit_params[7] == '{"added": ["member-role"], "removed": ["pre-member-role"]}'
	assert conn.committed


def test_promotion_without_audit_context_records_nothing(monkeypatch):
	conn = _FakeConnection(is_pre_member=False, is_paid=False)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	_promote(require_eligibility=False)

	assert not any("role_audit_logs" in sql for sql in conn.executed)
