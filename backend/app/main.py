"""役割: FastAPI起動点"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.manifest import router as manifest_router
from app.api.v1.roles import router as roles_router
from app.api.v1.sync import router as sync_router
from app.db.repository import init_db


app = FastAPI(title="AuthWebApp Backend", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
	init_db()


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


app.include_router(manifest_router)
app.include_router(roles_router)
app.include_router(sync_router)
