"""テスト用の Starlette Request を作る（エンドポイント関数を直接呼ぶテスト向け）"""

from starlette.requests import Request


def make_request(client_host: str = "192.0.2.1", headers: dict[str, str] | None = None) -> Request:
	raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
	return Request({"type": "http", "headers": raw_headers, "client": (client_host, 12345)})
