"""役割: FastAPI起動点"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.manifest import router as manifest_router
from app.api.v1.roles import router as roles_router
from app.api.v1.sync import router as sync_router
from app.api.v1.users import router as users_router
from app.api.v1.join import router as join_router
from app.api.v1.contact import router as contact_router
from app.api.v1.student import router as student_router
from app.api.v1.members import router as members_router
from app.api.v1.survey import router as survey_router
from app.db.repository import init_db


# 環境判定（本番環境では OpenAPI docs や開発用APIを遮断）
_fastapi_env = os.getenv("FASTAPI_ENV", "").strip().lower()
_is_prod = _fastapi_env == "production"
_is_dev = _fastapi_env in ("development", "dev", "local")

app = FastAPI(
	title="AuthWebApp Backend",
	version="0.1.0",
	docs_url=None if _is_prod else "/docs",
	redoc_url=None if _is_prod else "/redoc",
	openapi_url=None if _is_prod else "/openapi.json",
)

# Build allowlist for CORS. Use FRONTEND_ORIGIN (comma-separated) when set,
# otherwise allow both localhost and 127.0.0.1 for local development.
env_frontend = os.getenv("FRONTEND_ORIGIN", "").strip()
if env_frontend:
	_origins = [origin.strip() for origin in env_frontend.split(",") if origin.strip()]
else:
	_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

# If frontend origin list contains localhost or 127.0.0.1, also add the
# counterpart variant so docker-compose defaults (which set FRONTEND_ORIGIN
# to http://localhost:5173) will still allow requests from http://127.0.0.1:5173.
expanded = set()
for o in _origins:
	expanded.add(o)
	if "localhost" in o and "127.0.0.1" not in o:
		expanded.add(o.replace("localhost", "127.0.0.1"))
	elif "127.0.0.1" in o and "localhost" not in o:
		expanded.add(o.replace("127.0.0.1", "localhost"))

_origins = list(expanded)

app.add_middleware(
	CORSMiddleware,
	allow_origins=_origins,
	# allow_origin_regex covers other local variants like http://localhost:5173/ and IPv4/IPv6 forms
	allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
	# DB初期化を環境変数 SKIP_DB_INIT でスキップ可能
	# SKIP_DB_INIT が "true" または未設定の場合は初期化をスキップ（デフォルト）
	# SKIP_DB_INIT が "false" の場合のみ初期化を実行
	skip_db_init = os.getenv("SKIP_DB_INIT", "true").lower() in ("true", "1", "yes")
	if not skip_db_init:
		init_db()


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


app.include_router(manifest_router)
app.include_router(roles_router)
app.include_router(sync_router)
app.include_router(users_router)
app.include_router(join_router)
app.include_router(contact_router)
app.include_router(student_router)
app.include_router(members_router)
app.include_router(survey_router)

# 開発環境専用: ロール切替API（本番環境では無効化 / Fail-Closed: 開発環境のみ明示的に登録）
if _is_dev and not _is_prod:
	from app.api.v1.dev import router as dev_router
	app.include_router(dev_router)
