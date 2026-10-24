"""テスト用の Starlette Request を作る（エンドポイント関数を直接呼ぶテスト向け）"""

from starlette.requests import Request

from app.db.audit_repository import AuditContext


def make_request(client_host: str = "192.0.2.1", headers: dict[str, str] | None = None) -> Request:
	raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
	return Request({"type": "http", "headers": raw_headers, "client": (client_host, 12345)})


# エンドポイント関数を直接呼ぶときに Depends(get_audit_context) の代わりに渡す値
TEST_AUDIT = AuditContext(request_id="test-request", actor_sub="test-sub", actor_discord_id=None)
