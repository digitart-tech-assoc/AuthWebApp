"""役割: マニフェストAPI"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field


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


# MVPのため in-memory で保持（将来は PostgreSQL に置換）
_manifest_store = Manifest(
	categories=[Category(id="cat-grade", name="学年", display_order=0, is_collapsed=False)],
	roles=[
		Role(
			role_id="sample-role-1",
			name="2024年",
			color="#22c55e",
			position=10,
			category_id="cat-grade",
		)
	],
)


@router.get("/manifest", response_model=Manifest)
async def get_manifest() -> Manifest:
	return _manifest_store


@router.put("/manifest", response_model=Manifest)
async def put_manifest(payload: Manifest) -> Manifest:
	global _manifest_store
	_manifest_store = payload
	return _manifest_store
