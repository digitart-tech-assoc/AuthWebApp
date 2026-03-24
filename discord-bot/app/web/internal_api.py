"""役割: 内部受信API"""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services.reconcile import run_reconcile


router = APIRouter(prefix="/internal", tags=["internal"])
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")


class SyncPayload(BaseModel):
	action: str = "sync_roles"


@router.post("/sync")
async def internal_sync(payload: SyncPayload, authorization: str | None = Header(default=None)) -> dict:
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")
	result = await run_reconcile()
	return {"received": payload.action, "result": result}


@router.get("/health")
async def internal_health() -> dict:
	return {"status": "ok"}
