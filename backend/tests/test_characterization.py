"""仕様固定テスト (Characterization Tests)

リファクタリング前に既存の振る舞いを固定するテスト。
DB依存なしで検証可能な純粋関数のみを対象とする。
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import pytest


# ============================================================================
# is_prospective_form_open — 入学見込みフォーム期間判定
# ============================================================================

class TestIsProspectiveFormOpen:
    """repository.is_prospective_form_open の仕様固定テスト"""

    def test_feb_1_returns_true(self, monkeypatch):
        from app.db.repository import is_prospective_form_open
        jst = timezone(timedelta(hours=9))
        fake_now = datetime(2026, 2, 1, 0, 0, 0, tzinfo=jst)
        monkeypatch.setattr("app.db.membership_repository.datetime", _FakeDatetime(fake_now))
        assert is_prospective_form_open() is True

    def test_march_15_returns_true(self, monkeypatch):
        from app.db.repository import is_prospective_form_open
        jst = timezone(timedelta(hours=9))
        fake_now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=jst)
        monkeypatch.setattr("app.db.membership_repository.datetime", _FakeDatetime(fake_now))
        assert is_prospective_form_open() is True

    def test_april_5_returns_true(self, monkeypatch):
        from app.db.repository import is_prospective_form_open
        jst = timezone(timedelta(hours=9))
        fake_now = datetime(2026, 4, 5, 23, 59, 59, tzinfo=jst)
        monkeypatch.setattr("app.db.membership_repository.datetime", _FakeDatetime(fake_now))
        assert is_prospective_form_open() is True

    def test_april_6_returns_false(self, monkeypatch):
        from app.db.repository import is_prospective_form_open
        jst = timezone(timedelta(hours=9))
        fake_now = datetime(2026, 4, 6, 0, 0, 0, tzinfo=jst)
        monkeypatch.setattr("app.db.membership_repository.datetime", _FakeDatetime(fake_now))
        assert is_prospective_form_open() is False

    def test_jan_31_returns_false(self, monkeypatch):
        from app.db.repository import is_prospective_form_open
        jst = timezone(timedelta(hours=9))
        fake_now = datetime(2026, 1, 31, 23, 59, 59, tzinfo=jst)
        monkeypatch.setattr("app.db.membership_repository.datetime", _FakeDatetime(fake_now))
        assert is_prospective_form_open() is False

    def test_december_returns_false(self, monkeypatch):
        from app.db.repository import is_prospective_form_open
        jst = timezone(timedelta(hours=9))
        fake_now = datetime(2026, 12, 25, 0, 0, 0, tzinfo=jst)
        monkeypatch.setattr("app.db.membership_repository.datetime", _FakeDatetime(fake_now))
        assert is_prospective_form_open() is False


class _FakeDatetime:
    """datetime.now() をモックするためのヘルパー"""

    def __init__(self, fixed_now: datetime):
        self._fixed_now = fixed_now

    def now(self, tz=None):
        if tz is not None:
            return self._fixed_now.astimezone(tz)
        return self._fixed_now

    def __call__(self, *args, **kwargs):
        return datetime(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(datetime, name)


# ============================================================================
# _generate_student_email — 学生番号→メールアドレス生成
# ============================================================================

class TestGenerateStudentEmail:
    """student._generate_student_email の仕様固定テスト"""

    def test_standard_with_a_prefix(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("A2312345") == "a2312345@aoyama.ac.jp"

    def test_standard_without_a_prefix(self):
        from app.api.v1.student import _generate_student_email
        # 先頭が "2" → head_map により "b" に変換される仕様
        assert _generate_student_email("2312345") == "b312345@aoyama.ac.jp"

    def test_pre_member_style_1(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("1A234567") == "aa234567@aoyama.ac.jp"

    def test_pre_member_style_2(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("2B345678") == "bb345678@aoyama.ac.jp"

    def test_pre_member_style_3(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("3C456789") == "cc456789@aoyama.ac.jp"

    def test_pre_member_style_4(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("4D567890") == "dd567890@aoyama.ac.jp"

    def test_pre_member_style_s(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("SA123456") == "sa123456@aoyama.ac.jp"

    def test_lowercase_a_prefix(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("a2312345") == "a2312345@aoyama.ac.jp"

    def test_whitespace_handling(self):
        from app.api.v1.student import _generate_student_email
        assert _generate_student_email("  A2312345  ") == "a2312345@aoyama.ac.jp"


# ============================================================================
# build_role_edit_payload / build_role_create_payload — Discord ペイロード生成
# ============================================================================

class TestBuildRoleEditPayload:
    """discord_client.build_role_edit_payload の仕様固定テスト"""

    def test_no_changes_returns_empty(self):
        from app.services.discord_client import build_role_edit_payload
        desired = {"name": "Test", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        actual = {"name": "Test", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        assert build_role_edit_payload(desired, actual) == {}

    def test_name_change(self):
        from app.services.discord_client import build_role_edit_payload
        desired = {"name": "NewName", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        actual = {"name": "OldName", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        result = build_role_edit_payload(desired, actual)
        assert result == {"name": "NewName"}

    def test_permission_change(self):
        from app.services.discord_client import build_role_edit_payload
        desired = {"name": "Test", "hoist": False, "mentionable": False, "permissions": 1024, "color": "#000000"}
        actual = {"name": "Test", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        result = build_role_edit_payload(desired, actual)
        assert result == {"permissions": "1024"}

    def test_color_change(self):
        from app.services.discord_client import build_role_edit_payload
        desired = {"name": "Test", "hoist": False, "mentionable": False, "permissions": 0, "color": "#ff0000"}
        actual = {"name": "Test", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        result = build_role_edit_payload(desired, actual)
        assert result == {"color": 0xff0000}

    def test_multiple_changes(self):
        from app.services.discord_client import build_role_edit_payload
        desired = {"name": "New", "hoist": True, "mentionable": True, "permissions": 8, "color": "#ff0000"}
        actual = {"name": "Old", "hoist": False, "mentionable": False, "permissions": 0, "color": "#000000"}
        result = build_role_edit_payload(desired, actual)
        assert "name" in result
        assert "hoist" in result
        assert "mentionable" in result
        assert "permissions" in result
        assert "color" in result


class TestBuildRoleCreatePayload:
    """discord_client.build_role_create_payload の仕様固定テスト"""

    def test_basic_payload(self):
        from app.services.discord_client import build_role_create_payload
        desired = {"name": "TestRole", "hoist": True, "mentionable": False, "permissions": 1024, "color": "#3498db"}
        result = build_role_create_payload(desired)
        assert result["name"] == "TestRole"
        assert result["hoist"] is True
        assert result["mentionable"] is False
        assert result["permissions"] == "1024"
        assert result["color"] == 0x3498db

    def test_defaults(self):
        from app.services.discord_client import build_role_create_payload
        desired = {"name": "MinimalRole"}
        result = build_role_create_payload(desired)
        assert result["name"] == "MinimalRole"
        assert result["hoist"] is False
        assert result["mentionable"] is False
        assert result["permissions"] == "0"
        assert result["color"] == 0


# ============================================================================
# Color conversion — 色変換ユーティリティ
# ============================================================================

class TestColorConversion:
    """discord_client の色変換関数の仕様固定テスト"""

    def test_int_to_hex_zero(self):
        from app.services.discord_client import _int_color_to_hex
        assert _int_color_to_hex(0) == "#000000"

    def test_int_to_hex_red(self):
        from app.services.discord_client import _int_color_to_hex
        assert _int_color_to_hex(0xff0000) == "#ff0000"

    def test_int_to_hex_white(self):
        from app.services.discord_client import _int_color_to_hex
        assert _int_color_to_hex(0xffffff) == "#ffffff"

    def test_hex_to_int_with_hash(self):
        from app.services.discord_client import _hex_color_to_int
        assert _hex_color_to_int("#ff0000") == 0xff0000

    def test_hex_to_int_without_hash(self):
        from app.services.discord_client import _hex_color_to_int
        assert _hex_color_to_int("3498db") == 0x3498db

    def test_hex_to_int_empty(self):
        from app.services.discord_client import _hex_color_to_int
        assert _hex_color_to_int("") == 0

    def test_hex_to_int_hash_only(self):
        from app.services.discord_client import _hex_color_to_int
        assert _hex_color_to_int("#") == 0


# ============================================================================
# expiry_from_assigned_at — 有効期限計算
# ============================================================================

class TestExpiryFromAssignedAt:
    """repository.expiry_from_assigned_at の仕様固定テスト"""

    def test_none_returns_none(self):
        from app.db.repository import expiry_from_assigned_at
        assert expiry_from_assigned_at(None) is None

    def test_june_returns_next_april_30(self):
        from app.db.repository import expiry_from_assigned_at
        # 2026年6月1日 JST → 2026年度 → 2027年4月30日 JST 23:59:59
        assigned = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = expiry_from_assigned_at(assigned)
        jst = ZoneInfo("Asia/Tokyo")
        result_jst = result.astimezone(jst)
        assert result_jst.year == 2027
        assert result_jst.month == 4
        assert result_jst.day == 30
        assert result_jst.hour == 23
        assert result_jst.minute == 59

    def test_march_returns_same_year_april_30(self):
        from app.db.repository import expiry_from_assigned_at
        # 2026年3月1日 JST → 2025年度 → 2026年4月30日 JST 23:59:59
        assigned = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = expiry_from_assigned_at(assigned)
        jst = ZoneInfo("Asia/Tokyo")
        result_jst = result.astimezone(jst)
        assert result_jst.year == 2026
        assert result_jst.month == 4
        assert result_jst.day == 30

    def test_naive_datetime_treated_as_utc(self):
        from app.db.repository import expiry_from_assigned_at
        assigned = datetime(2026, 5, 1, 0, 0, 0)  # naive
        result = expiry_from_assigned_at(assigned)
        assert result is not None
        assert result.tzinfo is not None


# ============================================================================
# OTP generation — OTPコード生成ユーティリティ
# ============================================================================

class TestOTPUtils:
    """utils.otp のOTP関連ユーティリティの仕様固定テスト"""

    def test_generate_otp_code_length(self):
        from app.utils.otp import generate_otp_code
        code = generate_otp_code()
        assert len(code) == 6

    def test_generate_otp_code_digits_only(self):
        from app.utils.otp import generate_otp_code
        code = generate_otp_code()
        assert code.isdigit()

    def test_hash_and_verify(self):
        from app.utils.otp import generate_otp_code, hash_otp_code, verify_otp_code
        code = generate_otp_code()
        hashed = hash_otp_code(code)
        assert verify_otp_code(code, hashed) is True
        assert verify_otp_code("000000", hashed) is False or code == "000000"

    def test_verify_wrong_code(self):
        from app.utils.otp import hash_otp_code, verify_otp_code
        hashed = hash_otp_code("123456")
        assert verify_otp_code("654321", hashed) is False

    def test_verify_invalid_hash(self):
        from app.utils.otp import verify_otp_code
        assert verify_otp_code("123456", "invalid_hash") is False


# ============================================================================
# student._generate_otp_code — student.py 内の OTP 生成
# ============================================================================

class TestStudentOTPGenerate:
    """student._generate_otp_code の仕様固定テスト"""

    def test_default_length(self):
        from app.api.v1.student import _generate_otp_code
        code = _generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_custom_length(self):
        from app.api.v1.student import _generate_otp_code
        code = _generate_otp_code(length=8)
        assert len(code) == 8
        assert code.isdigit()


# ============================================================================
# membership_repository — ボイラープレート統合テスト
# ============================================================================

class TestMembershipBoilerplate:
    """has_membership, get_membership_count およびラッパーのテスト"""

    def test_has_membership_true(self):
        from unittest.mock import MagicMock, patch
        from app.db.membership_repository import has_membership

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (1,)

        with patch("app.db.membership_repository._connect", return_value=MagicMock(__enter__=MagicMock(return_value=mock_conn))):
            assert has_membership("user123", "admin") is True
            sql, params = mock_cur.execute.call_args[0]
            assert "ANY(%s)" in sql
            assert params == ("user123", ["admin"])

    def test_has_membership_false(self):
        from unittest.mock import MagicMock, patch
        from app.db.membership_repository import has_membership

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = None

        with patch("app.db.membership_repository._connect", return_value=MagicMock(__enter__=MagicMock(return_value=mock_conn))):
            assert has_membership("user123", "admin") is False

    def test_is_member_wrapper(self):
        from unittest.mock import MagicMock, patch
        from app.db.membership_repository import is_member

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (1,)

        with patch("app.db.membership_repository._connect", return_value=MagicMock(__enter__=MagicMock(return_value=mock_conn))):
            assert is_member("user123") is True
            params = mock_cur.execute.call_args[0][1]
            assert params == ("user123", ["member", "sub_user"])

    def test_is_admin_wrapper(self):
        from unittest.mock import MagicMock, patch
        from app.db.membership_repository import is_admin

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (1,)

        with patch("app.db.membership_repository._connect", return_value=MagicMock(__enter__=MagicMock(return_value=mock_conn))):
            assert is_admin("user123") is True
            params = mock_cur.execute.call_args[0][1]
            assert params == ("user123", ["admin"])

    def test_get_membership_count(self):
        from unittest.mock import MagicMock, patch
        from app.db.membership_repository import get_membership_count, get_member_user_count

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (42,)

        with patch("app.db.membership_repository._connect", return_value=MagicMock(__enter__=MagicMock(return_value=mock_conn))):
            assert get_membership_count("member") == 42
            assert get_member_user_count() == 42


# ============================================================================
# Supabase JWT Decode — ES256 / HS256 検証
# ============================================================================

class TestSupabaseJWTDecode:
    """_decode_supabase_token の ES256/JWKS および HS256 テスト"""

    def test_decode_hs256_token(self, monkeypatch):
        import jwt
        from app.core.auth import _decode_supabase_token

        secret = "test-secret-key-12345678901234567890"
        monkeypatch.setattr("app.core.auth.SUPABASE_JWT_SECRET", secret)
        monkeypatch.setattr("app.core.auth.jwks_client", None)

        payload = {
            "sub": "user-uuid-123",
            "aud": "authenticated",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        claims = _decode_supabase_token(token)
        assert claims["sub"] == "user-uuid-123"

    def test_decode_es256_with_mock_jwks(self, monkeypatch):
        from unittest.mock import MagicMock
        from app.core.auth import _decode_supabase_token
        import jwt
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization

        # テスト用 EC 秘密鍵・公開鍵を生成
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        mock_jwks = MagicMock()
        mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key

        monkeypatch.setattr("app.core.auth.jwks_client", mock_jwks)
        monkeypatch.setattr("app.core.auth.SUPABASE_ISSUER_URL", "")

        payload = {
            "sub": "user-uuid-es256",
            "aud": "authenticated",
            "iss": "https://test.supabase.co/auth/v1",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, private_key, algorithm="ES256")
        claims = _decode_supabase_token(token)
        assert claims["sub"] == "user-uuid-es256"
        assert claims["iss"] == "https://test.supabase.co/auth/v1"


