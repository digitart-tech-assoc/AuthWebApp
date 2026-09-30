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
    async def test_self_batch_compensates_on_db_failure(self):
        """DB 保存失敗時に Discord のロール一覧を元に戻す"""
        from app.api.v1.roles import SelfBatchPayload, self_batch_roles
        from fastapi import HTTPException

        payload = SelfBatchPayload(roles_to_add=["role-123"], roles_to_remove=[])
        principal = {"discord_id": "user-456", "app_role": "member"}

        with patch("app.api.v1.roles._get_token", return_value="token"):
            with patch("app.api.v1.roles.fetch_manifest", return_value={"roles": [{"role_id": "role-123", "name": "Test", "category_id": "cat-open", "permissions": 0}], "categories": [{"id": "cat-open", "name": "趣味", "is_restricted": False}]}):
                with patch("app.api.v1.roles.fetch_guild_roles", new_callable=AsyncMock, return_value=[{"role_id": "role-123", "position": 1, "managed": False}, {"role_id": "role-existing", "position": 1, "managed": False}]):
                    with patch("app.api.v1.roles.fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": ["role-existing"]}):
                        with patch("app.api.v1.roles.set_member_roles", new_callable=AsyncMock) as mock_set:
                            with patch("app.api.v1.roles.batch_update_user_roles", side_effect=Exception("DB connection error")):
                                with pytest.raises(HTTPException) as exc_info:
                                    await self_batch_roles(payload, principal)

                                assert exc_info.value.status_code == 500
                                assert "Discord state was reverted" in str(exc_info.value.detail)
                                assert mock_set.await_count == 2
                                assert mock_set.await_args_list[1].args[2] == ["role-existing"]

    @pytest.mark.asyncio
    async def test_self_batch_rejects_conflicting_role_operations(self):
        """同じロールの付与と解除を同時に受け付けない"""
        from app.api.v1.roles import SelfBatchPayload, self_batch_roles
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await self_batch_roles(
                SelfBatchPayload(roles_to_add=["role-123"], roles_to_remove=["role-123"]),
                {"discord_id": "user-456", "app_role": "member"},
            )

        assert exc_info.value.status_code == 400


class TestSelfBatchWhitelistValidation:
    """セルフロール操作のホワイトリスト方式バリデーションのテスト"""

    PRINCIPAL = {"discord_id": "user-456", "app_role": "member"}
    CATEGORIES = [
        {"id": "cat-open", "name": "趣味", "is_restricted": False},
        {"id": "cat-restricted", "name": "運営", "is_restricted": True},
        {"id": "cat-reserved", "name": "学年", "is_restricted": False},
        {"id": "cat-flag-missing", "name": "フラグ欠損"},
    ]

    async def _call(self, role: dict, *, add: bool = True):
        from app.api.v1.roles import SelfBatchPayload, self_batch_roles

        manifest = {"roles": [{"role_id": "role-x", "name": "X", **role}], "categories": self.CATEGORIES}
        payload = SelfBatchPayload(
            roles_to_add=["role-x"] if add else [],
            roles_to_remove=[] if add else ["role-x"],
        )
        with patch("app.api.v1.roles._get_token", return_value="token"):
            with patch("app.api.v1.roles.fetch_manifest", return_value=manifest):
                with patch("app.api.v1.roles.fetch_guild_roles", new_callable=AsyncMock, return_value=[{"role_id": "role-x", "position": 1, "managed": False}]):
                    with patch("app.api.v1.roles.fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": [] if add else ["role-x"]}):
                        with patch("app.api.v1.roles.set_member_roles", new_callable=AsyncMock) as mock_set:
                            with patch("app.api.v1.roles.batch_update_user_roles"):
                                result = await self_batch_roles(payload, self.PRINCIPAL)
                                return result, mock_set

    async def _assert_forbidden(self, role: dict, reason: str, *, add: bool = True):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await self._call(role, add=add)
        assert exc_info.value.status_code == 403
        assert reason in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_rejects_role_without_category(self):
        """カテゴリ未設定のロールは付与できない"""
        await self._assert_forbidden({"category_id": None, "permissions": 0}, "カテゴリ未設定")

    @pytest.mark.asyncio
    async def test_rejects_role_without_category_on_remove(self):
        """カテゴリ未設定のロールは解除もできない"""
        await self._assert_forbidden({"category_id": None, "permissions": 0}, "カテゴリ未設定", add=False)

    @pytest.mark.asyncio
    async def test_rejects_role_in_unknown_category(self):
        """マニフェストに存在しないカテゴリのロールは付与できない"""
        await self._assert_forbidden({"category_id": "cat-deleted", "permissions": 0}, "禁止カテゴリ")

    @pytest.mark.asyncio
    async def test_rejects_role_in_restricted_category(self):
        """is_restricted = true のカテゴリのロールは付与できない"""
        await self._assert_forbidden({"category_id": "cat-restricted", "permissions": 0}, "禁止カテゴリ")

    @pytest.mark.asyncio
    async def test_rejects_role_in_reserved_category(self):
        """予約名カテゴリのロールは is_restricted = false でも付与できない"""
        await self._assert_forbidden({"category_id": "cat-reserved", "permissions": 0}, "禁止カテゴリ")

    @pytest.mark.asyncio
    async def test_rejects_role_when_restricted_flag_missing(self):
        """is_restricted が欠損しているカテゴリは拒否側に倒す"""
        await self._assert_forbidden({"category_id": "cat-flag-missing", "permissions": 0}, "禁止カテゴリ")

    @pytest.mark.asyncio
    async def test_rejects_role_with_permissions(self):
        """マニフェスト上の permissions が 0 以外のロールは付与できない"""
        await self._assert_forbidden({"category_id": "cat-open", "permissions": 8}, "Discord権限付き")

    @pytest.mark.asyncio
    async def test_allows_plain_role_in_open_category(self):
        """許可カテゴリ内の permissions = 0 のロールは付与できる"""
        result, mock_set = await self._call({"category_id": "cat-open", "permissions": 0})
        assert result["ok"] is True
        assert result["added"] == ["role-x"]
        mock_set.assert_awaited_once()
