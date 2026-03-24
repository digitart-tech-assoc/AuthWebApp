"""役割: 同期トリガーAPI"""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services.bot_client import notify_bot_sync


router = APIRouter(prefix="/api/v1", tags=["sync"])
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")


class SyncRequest(BaseModel):
	action: str = "sync_roles"


@router.post("/sync")
async def trigger_sync(payload: SyncRequest, authorization: str | None = Header(default=None)) -> dict:
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")
	result = await notify_bot_sync()
	return {"ok": result["status_code"] == 200, "bot": result}
