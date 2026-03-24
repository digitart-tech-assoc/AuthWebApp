"""役割: マニフェストAPI"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db.repository import fetch_manifest, save_manifest


router = APIRouter(prefix="/api/v1", tags=["manifest"])


class Category(BaseModel):
	id: str
	name: str
	display_order: int = 0
	is_collapsed: bool = False


class Role(BaseModel):
	role_id: str
	name: str
	color: str = "#000000"
	hoist: bool = False
	mentionable: bool = False
	permissions: int = 0
	position: int
	category_id: str | None = None


class Manifest(BaseModel):
	categories: list[Category] = Field(default_factory=list)
	roles: list[Role] = Field(default_factory=list)


@router.get("/manifest", response_model=Manifest)
async def get_manifest() -> Manifest:
	data = await asyncio.to_thread(fetch_manifest)
	return Manifest(**data)


@router.put("/manifest", response_model=Manifest)
async def put_manifest(payload: Manifest) -> Manifest:
	await asyncio.to_thread(
		save_manifest,
		[c.model_dump() for c in payload.categories],
		[r.model_dump() for r in payload.roles],
	)
	return payload
