"""役割: Discord Bot の内部同期エンドポイント URL を解決する（#173）

Bot の URL は環境変数 `BOT_INTERNAL_URL`（docker-compose・k8s が設定する名前）で指定する。
互換のため、未設定のときだけ旧名の `DISCORD_BOT_URL` を読む。
`BOT_INTERNAL_URL` は、ホストまでの URL（`http://host:8000`）でも、`/internal/sync` までを含む URL でもよい。
"""

from __future__ import annotations

import os

DEFAULT_BOT_URL = "http://discord-bot:8000"
BOT_SYNC_PATH = "/internal/sync"


def get_bot_sync_endpoint() -> str:
	"""Bot の `/internal/sync` エンドポイントの URL を返す（呼び出しごとに環境変数を読む）"""
	base = (os.getenv("BOT_INTERNAL_URL") or os.getenv("DISCORD_BOT_URL") or DEFAULT_BOT_URL).strip().rstrip("/")
	if base.endswith(BOT_SYNC_PATH):
		return base
	return f"{base}{BOT_SYNC_PATH}"
