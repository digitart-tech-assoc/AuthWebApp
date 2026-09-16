"""Copilot レビュー指摘事項修正の動作確認テスト"""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.utils.otp import verify_otp_code


class TestOTPPlaintextFallback:
    """平文 OTP の安全なフォールバック検証テスト"""

    def test_legacy_plaintext_match(self):
        """レガシー平文 OTP が一致した場合に True を返す"""
        assert verify_otp_code("123456", "123456") is True

    def test_legacy_plaintext_mismatch(self):
        """レガシー平文 OTP が不一致の場合に False を返す"""
        assert verify_otp_code("123456", "654321") is False


class TestBrevoExpiryFormatting:
    """Brevo OTP メールの有効期限文面テスト"""

    @pytest.mark.asyncio
    async def test_send_otp_email_custom_expiry(self):
        """expires_in_minutes がメール本文に正しく反映される"""
        from app.services.brevo_client import BrevoClient

        client = BrevoClient.__new__(BrevoClient)
        client.api_key = "test_key"
        client.base_url = "https://api.brevo.com/v3"
        client.sender_email = "test@example.com"
        client.sender_name = "Test Sender"

        captured_payload = None

        async def fake_send_smtp_email(payload, operation_name):
            nonlocal captured_payload
            captured_payload = payload
            return {"status": "success", "message_id": "msg-123"}

        client._send_smtp_email = fake_send_smtp_email

        await client.send_otp_email(
            email="student@example.com",
            code="123456",
            name="太郎",
            form_type="prospective-student",
            expires_in_minutes=20,
        )

        assert captured_payload is not None
        assert "20 分以内" in captured_payload["htmlContent"]
        assert "20 分以内" in captured_payload["textContent"]


class TestDiscordClientExceptionReRaise:
    """Discord クライアント例外の再送出テスト"""

    @pytest.mark.asyncio
    async def test_fetch_guild_members_with_role_raises_on_error(self):
        """ページネーション取得中にエラーが発生した場合に例外を再送出する"""
        from app.services.discord_client import fetch_guild_members_with_role

        with patch("httpx.AsyncClient.get", side_effect=Exception("Discord network timeout")):
            with pytest.raises(Exception, match="Discord network timeout"):
                await fetch_guild_members_with_role("guild-123", "role-456", "bot-token")


class TestRolesCompensationTransactions:
    """セルフロール操作での DB 失敗時補償ロールバックのテスト"""

    @pytest.mark.asyncio
    async def test_self_assign_compensates_on_db_failure(self):
        """DB 保存失敗時に Discord のロール付与を取り消す"""
        from app.api.v1.roles import self_assign_role, SelfAssignPayload
        from fastapi import HTTPException

        payload = SelfAssignPayload(role_id="role-123")
        principal = {"discord_id": "user-456", "app_role": "member"}

        with patch("app.api.v1.roles._validate_self_role_operation", return_value=({"role_id": "role-123"}, "user-456", "token")):
            with patch("app.api.v1.roles.add_role_to_member", new_callable=AsyncMock) as mock_add:
                with patch("app.api.v1.roles.remove_role_from_member", new_callable=AsyncMock) as mock_remove:
                    with patch("app.api.v1.roles.add_user_to_role", side_effect=Exception("DB connection error")):
                        with pytest.raises(HTTPException) as exc_info:
                            await self_assign_role(payload, principal)

                        assert exc_info.value.status_code == 500
                        # Discord に一旦付与されたが
                        mock_add.assert_awaited_once()
                        # DB エラーにより取り消し（補償）が呼ばれた
                        mock_remove.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_self_remove_compensates_on_db_failure(self):
        """DB 削除失敗時に Discord のロール解除を元に戻す"""
        from app.api.v1.roles import self_remove_role, SelfAssignPayload
        from fastapi import HTTPException

        payload = SelfAssignPayload(role_id="role-123")
        principal = {"discord_id": "user-456", "app_role": "member"}

        with patch("app.api.v1.roles._validate_self_role_operation", return_value=({"role_id": "role-123"}, "user-456", "token")):
            with patch("app.api.v1.roles.remove_role_from_member", new_callable=AsyncMock) as mock_remove:
                with patch("app.api.v1.roles.add_role_to_member", new_callable=AsyncMock) as mock_add:
                    with patch("app.api.v1.roles.remove_user_from_role", side_effect=Exception("DB connection error")):
                        with pytest.raises(HTTPException) as exc_info:
                            await self_remove_role(payload, principal)

                        assert exc_info.value.status_code == 500
                        # Discord から一旦削除されたが
                        mock_remove.assert_awaited_once()
                        # DB エラーにより再付与（補償）が呼ばれた
                        mock_add.assert_awaited_once()
