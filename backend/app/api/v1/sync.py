"""役割: 同期トリガーAPI"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_principal
from app.services.bot_client import notify_bot_sync


router = APIRouter(prefix="/api/v1", tags=["sync"])


class SyncRequest(BaseModel):
	action: str = "sync_roles"


@router.post("/sync")
async def trigger_sync(payload: SyncRequest, _principal: dict = Depends(get_current_principal)) -> dict:
	result = await notify_bot_sync()
	return {"ok": result["status_code"] == 200, "bot": result}
