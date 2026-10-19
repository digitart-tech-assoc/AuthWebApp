"""削除したエンドポイントが公開されていないことを検証するテスト（#211）。

- POST /api/v1/sync: 呼び出し元がなく、ログインしていれば未入会ユーザーでも Bot の reconcile を起動できたため削除した。
- POST /api/v1/roles/refresh: DB を Desired State とするロール管理と逆向きに、Discord の状態で DB を作り直す処理のため削除した。
"""

import pytest
from fastapi.testclient import TestClient

from app import main

REMOVED_PATHS = ["/api/v1/sync", "/api/v1/roles/refresh"]


@pytest.fixture
def client():
	# lifespan（DB 初期化・プール破棄）は走らせない
	return TestClient(main.app)


@pytest.fixture
def openapi_paths():
	# app.routes は include_router したルーターを展開しないことがあるため、OpenAPI スキーマで確認する。
	# 本番では /openapi.json を公開しないため、エンドポイント経由ではなく app.openapi() を直接使う
	return main.app.openapi()["paths"]


@pytest.mark.parametrize("path", REMOVED_PATHS)
def test_removed_endpoint_is_not_in_openapi(openapi_paths, path):
	assert path not in openapi_paths


@pytest.mark.parametrize("path", REMOVED_PATHS)
def test_removed_endpoint_returns_404(client, path):
	response = client.post(path, headers={"Authorization": "Bearer dummy"})

	assert response.status_code == 404


def test_role_push_endpoint_is_still_available(openapi_paths):
	# Bot への reconcile 依頼は push から行うため、push は残っていること
	assert "post" in openapi_paths["/api/v1/roles/push"]
