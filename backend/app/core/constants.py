"""役割: 共通定数定義

環境判定やシステム横断で利用される定数を管理する。
"""

from __future__ import annotations

# 開発環境とみなす FASTAPI_ENV の値（ホワイトリスト）
DEV_ENVS: frozenset[str] = frozenset({"development", "dev", "local"})
_DEV_ENVS: frozenset[str] = DEV_ENVS
