"""役割: マニフェストAPI"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.roles import fetch_protected_role_ids
from app.core.auth import require_admin, require_member
from app.core.exceptions import MembershipAssignmentError, ProtectedRoleAssignmentError
from app.core.membership_roles import membership_role_ids
from app.db.audit_repository import OP_MANIFEST_PATCH, OP_MANIFEST_PUT, AuditContext, get_audit_context
from app.db.repository import fetch_manifest, patch_manifest_db, replace_manifest


router = APIRouter(prefix="/api/v1", tags=["manifest"])


class Category(BaseModel):
	id: str
	name: str
	display_order: int = 0
	is_collapsed: bool = False
	permissions: int = 0
	is_restricted: bool = False


class Role(BaseModel):
	role_id: str
	name: str
	color: str = "#000000"
	hoist: bool = False
	mentionable: bool = False
	permissions: int = 0
	position: int
	category_id: str | None = None
	is_our_bot: bool = False
	# 会員種別のロールなら種別名（GET でだけ返す。保存では使わない。#251）
	membership_type: str | None = None


class Manifest(BaseModel):
	categories: list[Category] = Field(default_factory=list)
	roles: list[Role] = Field(default_factory=list)
	role_assignments: dict[str, list[str]] = Field(default_factory=dict)


class ManifestPatch(BaseModel):
	upsert_categories: list[Category] = Field(default_factory=list)
	delete_category_ids: list[str] = Field(default_factory=list)
	upsert_roles: list[Role] = Field(default_factory=list)
	delete_role_ids: list[str] = Field(default_factory=list)
	upsert_role_assignments: dict[str, list[str]] = Field(default_factory=dict)


def _role_membership_types() -> dict[str, str]:
	"""ロール ID -> 会員種別（環境変数で設定した種別のロールだけ）。"""
	return {role_id: m_type for m_type, ids in membership_role_ids().items() for role_id in ids}


async def _protected_role_ids_for(assignments: dict[str, list[str]]) -> frozenset[str]:
	"""割当を保存するときだけ、Discord で直接付け外しするロールを Discord から取得する。"""
	if not assignments:
		return frozenset()
	return await fetch_protected_role_ids()


async def _save(func, *args, protected_role_ids: frozenset[str]) -> None:
	"""保存を実行し、割当の検証エラーを HTTP エラーにする（#251）。"""
	try:
		await asyncio.to_thread(func, *args, protected_role_ids=protected_role_ids)
	except ProtectedRoleAssignmentError as exc:
		# 固定文言にロール ID だけを埋めたもの（app/core/exceptions.py）
		raise HTTPException(status_code=403, detail=exc.response_detail) from exc
	except MembershipAssignmentError as exc:
		# 固定文言に Discord ID と種別名だけを埋めたもの（app/core/exceptions.py）
		raise HTTPException(status_code=400, detail=exc.response_detail) from exc


@router.get("/manifest", response_model=Manifest)
async def get_manifest(_principal: dict = Depends(require_member)) -> Manifest:
	"""マニフェスト取得。member / sub_user / obog / admin のみ許可。"""
	data = await asyncio.to_thread(fetch_manifest)
	role_types = _role_membership_types()
	for role in data.get("roles", []):
		role["membership_type"] = role_types.get(role["role_id"])
	return Manifest(**data)


@router.put("/manifest", response_model=Manifest)
async def put_manifest(
	payload: Manifest,
	_principal: dict = Depends(require_admin),
	audit: AuditContext = Depends(get_audit_context),
) -> Manifest:
	"""マニフェスト保存。admin のみ許可。

	会員種別のロールの割当を変えると、user_memberships も更新する。種別として成り立たない割当は 400 を返す。
	Discord で直接付け外しするロールの割当を変えようとした場合は 403 を返す（#251）。
	"""
	await _save(
		replace_manifest,
		[c.model_dump() for c in payload.categories],
		[r.model_dump() for r in payload.roles],
		payload.role_assignments,
		audit.with_operation(OP_MANIFEST_PUT),
		protected_role_ids=await _protected_role_ids_for(payload.role_assignments),
	)
	return payload


@router.patch("/manifest")
async def patch_manifest(
	payload: ManifestPatch,
	_principal: dict = Depends(require_admin),
	audit: AuditContext = Depends(get_audit_context),
) -> dict:
	"""マニフェスト差分保存。admin のみ許可。

	会員種別のロールの割当を変えると、user_memberships も更新する。種別として成り立たない割当は 400 を返す。
	Discord で直接付け外しするロールの割当を変えようとした場合は 403 を返す（#251）。
	"""
	await _save(
		patch_manifest_db,
		[c.model_dump() for c in payload.upsert_categories],
		payload.delete_category_ids,
		[r.model_dump() for r in payload.upsert_roles],
		payload.delete_role_ids,
		payload.upsert_role_assignments,
		audit.with_operation(OP_MANIFEST_PATCH),
		protected_role_ids=await _protected_role_ids_for(payload.upsert_role_assignments),
	)
	return {"ok": True}
