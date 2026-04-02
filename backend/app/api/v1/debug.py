"""役割: 開発時の内部デバッグ用 API

保護: `Authorization: Bearer <SHARED_SECRET>` ヘッダを要求します。
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.db import repository

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")


@router.get("/db_check")
async def db_check(authorization: str | None = Header(default=None)) -> JSONResponse:
    """内部向け: DATABASE_URL の解析と簡易接続確認を行う。

    レスポンスにはホスト/ポート/ユーザ名を含めますが、パスワードは返しません。
    """
    expected = f"Bearer {SHARED_SECRET}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    dsn = repository.DATABASE_URL
    parsed = urlparse(dsn or "")
    host = parsed.hostname
    port = parsed.port
    user = parsed.username
    database = parsed.path.lstrip("/") if parsed.path else None

    try:
        # repository._connect() は接続タイムアウトや sslmode を扱うように実装済み
        with repository._connect() as conn:
            return JSONResponse(status_code=200, content={
                "ok": True,
                "host": host,
                "port": port,
                "user": user,
                "database": database,
                "message": "DB connection succeeded",
            })
    except Exception as e:
        err = str(e)
        hints: list[str] = []
        if "tenant or user not found" in err.lower() or "tenant or user not found" in err:
            hints.append("認証に失敗しています: DATABASE_URL の user/password が正しいか、Supabase の Pooler 接続文字列を使用しているか確認してください.")
        if "could not translate host name" in err.lower():
            hints.append("ホスト名が解決できません: DNS/ネットワークを確認してください.")
        if not hints:
            hints.append("ログの完全な内容を確認してください。")

        return JSONResponse(status_code=500, content={
            "ok": False,
            "host": host,
            "port": port,
            "user": user,
            "database": database,
            "error": err,
            "hints": hints,
        })
