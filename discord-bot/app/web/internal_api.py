"""役割: 内部受信API"""

from __future__ import annotations

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.services.reconcile import run_reconcile
from app.shared_secret import verify_internal_authorization


router = APIRouter(prefix="/internal", tags=["internal"])


class SyncPayload(BaseModel):
	action: str = "sync_roles"


@router.post("/sync")
async def internal_sync(payload: SyncPayload, authorization: str | None = Header(default=None)) -> dict:
	verify_internal_authorization(authorization)
	result = await run_reconcile()
	return {"received": payload.action, "result": result}


@router.get("/health")
async def internal_health() -> dict:
	return {"status": "ok"}
