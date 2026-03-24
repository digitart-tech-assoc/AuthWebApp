"""役割: FastAPI起動点"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.manifest import router as manifest_router
from app.api.v1.sync import router as sync_router


app = FastAPI(title="AuthWebApp Backend", version="0.1.0")


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


app.include_router(manifest_router)
app.include_router(sync_router)
