"""Survey endpoints for member registration"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List

from app.core.auth import get_current_principal
from app.db import repository

router = APIRouter(prefix="/api/v1/survey", tags=["survey"])


class SurveyRequest(BaseModel):
    digitart_channels: List[str] = Field(default_factory=list)
    digitart_channels_other: str | None = None

    circle_search_channels: List[str] = Field(default_factory=list)
    circle_search_other: str | None = None

    discord_invite_source: str | None = None
    discord_invite_other: str | None = None

    interested_fields: List[str] = Field(default_factory=list)
    interested_fields_other: str | None = None

    motivations: List[str] = Field(default_factory=list)
    motivations_other: str | None = None

    join_request_id: str | None = None


class SurveyResponse(BaseModel):
    id: int
    created_at: str | None


@router.post("/", response_model=SurveyResponse)
async def submit_survey(req: SurveyRequest, principal: dict = Depends(get_current_principal)) -> SurveyResponse:
    """Save survey answers. Requires linked Discord account (principal)."""
    discord_id = principal.get("discord_id")
    auth_type = principal.get("auth_type")
    # Allow internal/shared-secret clients (auth_type == "internal") to submit without a discord_id
    if not discord_id and auth_type != "internal":
        raise HTTPException(status_code=401, detail="Discord account not linked")

    # Try to resolve profile by discord_id
    profile = repository._get_student_profile(discord_id) if hasattr(repository, "_get_student_profile") else None
    profile_id = profile.get("id") if profile else None
    student_number = profile.get("student_number") if profile else ""

    payload = req.dict()

    try:
        result = repository.save_member_survey_response(profile_id, student_number or "", req.join_request_id, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save survey response: {e}")

    return SurveyResponse(id=result.get("id"), created_at=result.get("created_at"))
