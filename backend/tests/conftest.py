"""pytest conftest — テスト用の共通フィクスチャ"""

import sys
import os

# backend ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.api.v1 import contact, join, student


@pytest.fixture(autouse=True)
def reset_rate_limiters():
	"""レート制限のカウントはモジュール変数に残るため、テストごとに消す"""
	limiters = [student._otp_send_limiter, join._request_limiter, contact._contact_limiter]
	for limiter in limiters:
		limiter.reset()
	yield
	for limiter in limiters:
		limiter.reset()
