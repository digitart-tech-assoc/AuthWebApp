"""upsert_student_profile_and_promote のトランザクション内資格検証のテスト"""

import pytest

from app.core.exceptions import RegistrationNotEligibleError
from app.db import student_repository


class _FakeCursor:
	def __init__(self, conn):
		self._conn = conn
		self._result = None

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def execute(self, sql, params=None):
		normalized = " ".join(sql.split())
		self._conn.executed.append(normalized)
		if "FROM user_memberships" in normalized and normalized.startswith("SELECT"):
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


def _promote(require_eligibility: bool = True) -> str:
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

	assert _promote() == "prof_test"

	assert "FOR UPDATE" in conn.executed[0] and "membership_type = 'pre_member'" in conn.executed[0]
	assert "FOR SHARE" in conn.executed[1] and "expires_at > now()" in conn.executed[1]
	assert any("UPDATE user_memberships" in sql for sql in _writes(conn))
	assert conn.committed


def test_promotion_skips_eligibility_check_for_registered_user(monkeypatch):
	conn = _FakeConnection(is_pre_member=False, is_paid=False)
	monkeypatch.setattr(student_repository, "_connect", lambda: conn)

	assert _promote(require_eligibility=False) == "prof_test"

	assert not any("FROM paid_invitations" in sql for sql in conn.executed)
	assert conn.committed
