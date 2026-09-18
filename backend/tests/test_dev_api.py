"""開発用ロール切替機能（dev API）のテスト"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from app.api.v1.dev import (
    _verify_dev_env,
    _get_current_state,
    _switch_role_tx,
    ALLOWED_ROLES,
)
from app.core.constants import DEV_ENVS


class TestDevEnvVerification:
    """環境変数判定（Fail-Closed / ホワイトリスト方式）のテスト"""

    @pytest.mark.parametrize("env_val", ["development", "dev", "local", "DEVELOPMENT", " DEV "])
    def test_verify_dev_env_allowed(self, env_val: str):
        """許可された開発環境値の場合は例外が発生しない"""
        with patch.dict(os.environ, {"FASTAPI_ENV": env_val}):
            _verify_dev_env()

    @pytest.mark.parametrize("env_val", ["production", "staging", "test", "", "unknown"])
    def test_verify_dev_env_blocked(self, env_val: str):
        """本番環境、未許可値、空文字の場合は 404 が発生する"""
        with patch.dict(os.environ, {"FASTAPI_ENV": env_val}):
            with pytest.raises(HTTPException) as exc_info:
                _verify_dev_env()
            assert exc_info.value.status_code == 404

    def test_verify_dev_env_unset_blocked(self):
        """環境変数自体が未設定の場合も 404 が発生する"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                _verify_dev_env()
            assert exc_info.value.status_code == 404


class TestGetCurrentState:
    """ロールおよび支払い状態の取得テスト"""

    @patch("app.api.v1.dev._connect")
    def test_get_current_state_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # 1回目の fetchone() はロール ("member")、2回目は paid_invitations (True)
        mock_cur.fetchone.side_effect = [("member",), (1,)]

        role, is_paid = _get_current_state("123456789")

        assert role == "member"
        assert is_paid is True
        mock_conn.close.assert_called_once()

    @patch("app.api.v1.dev._connect")
    def test_get_current_state_none_and_unpaid(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        mock_cur.fetchone.side_effect = [None, None]

        role, is_paid = _get_current_state("123456789")

        assert role == "none"
        assert is_paid is False
        mock_conn.close.assert_called_once()

    @patch("app.api.v1.dev._connect")
    def test_get_current_state_connection_closed_on_error(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.execute.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            _get_current_state("123456789")

        mock_conn.close.assert_called_once()


class TestSwitchRoleTx:
    """単一トランザクションでのロール切替テスト"""

    @patch("app.api.v1.dev._connect")
    def test_switch_role_tx_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        _switch_role_tx("123456789", "member", True)

        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        assert mock_cur.execute.call_count == 4  # delete x2, insert membership, insert paid

    @patch("app.api.v1.dev._connect")
    def test_switch_role_tx_none_role(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        _switch_role_tx("123456789", "none", False)

        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        assert mock_cur.execute.call_count == 2  # delete x2 only

    @patch("app.api.v1.dev._connect")
    def test_switch_role_tx_rollback_on_error(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.execute.side_effect = RuntimeError("DB write failure")

        with pytest.raises(RuntimeError):
            _switch_role_tx("123456789", "admin", False)

        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()
