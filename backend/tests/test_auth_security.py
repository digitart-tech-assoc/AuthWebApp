from __future__ import annotations

import pytest
from app.core.auth import _extract_verified_discord_id


class TestExtractVerifiedDiscordId:
    def test_extract_from_identities(self):
        claims = {
            "sub": "user-uuid-1",
            "app_metadata": {"provider": "discord"},
            "identities": [
                {"provider": "discord", "id": "123456789012345678"}
            ],
            "user_metadata": {"provider_id": "malicious_fake_id"},
        }
        # identities が最優先され、user_metadata の改ざん値は無視される
        result = _extract_verified_discord_id(claims)
        assert result == "123456789012345678"

    def test_extract_from_discord_provider_metadata(self):
        claims = {
            "sub": "user-uuid-2",
            "app_metadata": {"provider": "discord", "providers": ["discord"]},
            "user_metadata": {"provider_id": "123456789012345678"},
        }
        result = _extract_verified_discord_id(claims)
        assert result == "123456789012345678"

    def test_reject_email_provider_spoofing_user_metadata(self):
        # Email 等でサインアップしたユーザーが user_metadata.provider_id を勝手に改ざんした場合
        claims = {
            "sub": "attacker-uuid",
            "app_metadata": {"provider": "email", "providers": ["email"]},
            "user_metadata": {"provider_id": "victim_admin_discord_id"},
        }
        result = _extract_verified_discord_id(claims)
        assert result is None  # 偽装が遮断されること

    def test_extract_from_app_metadata_discord_id(self):
        claims = {
            "sub": "user-uuid-3",
            "app_metadata": {"provider": "discord", "discord_id": "123456789012345678"},
            "user_metadata": {},
        }
        result = _extract_verified_discord_id(claims)
        assert result == "123456789012345678"

    def test_no_claims(self):
        assert _extract_verified_discord_id({}) is None
