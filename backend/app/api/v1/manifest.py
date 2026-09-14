"""役割: マニフェストAPI"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_admin, require_member
from app.db.repository import fetch_manifest, save_manifest, save_role_assignments, patch_manifest_db
from fastapi import HTTPException


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

@router.get("/manifest", response_model=Manifest)
async def get_manifest(_principal: dict = Depends(require_member)) -> Manifest:
	"""マニフェスト取得。member / obog / admin のみ許可。"""
	data = await asyncio.to_thread(fetch_manifest)
	return Manifest(**data)


@router.put("/manifest", response_model=Manifest)
async def put_manifest(payload: Manifest, principal: dict = Depends(require_member)) -> Manifest:
	"""マニフェスト保存。member はロール権限変更不可。新規ロール時は会員情報カテゴリのみ権限設定可。ロール削除時はメンバー割り当て不可。"""
	is_admin = principal.get("app_role") == "admin"
	
	if not is_admin:
		# member の場合、permissions 変更またはロール作成時の権限設定を検出して拒否
		current_data = await asyncio.to_thread(fetch_manifest)
		current_roles_map = {role["role_id"]: role for role in current_data.get("roles", [])}
		current_cats_map = {cat["id"]: cat for cat in current_data.get("categories", [])}
		role_assignments = current_data.get("role_assignments", {})
		
		# 削除対象ロールの検出（current に存在して新規の payload に含まれない）
		new_role_ids = {role.role_id for role in payload.roles}
		deleted_role_ids = set(current_roles_map.keys()) - new_role_ids
		
		# member がロール削除する場合、メンバー割り当てがないか確認
		for deleted_role_id in deleted_role_ids:
			assigned_members = role_assignments.get(deleted_role_id, [])
			if assigned_members:
				raise HTTPException(status_code=403, detail=f"Member cannot delete role with assigned members ({len(assigned_members)} members)")
		
		for new_role in payload.roles:
			current_role = current_roles_map.get(new_role.role_id)
			is_new_role = current_role is None  # 新規ロール（DBに未登録）
			
			if is_new_role:
				# 新規ロール: 会員情報カテゴリ以外なら permissions=0 必須
				category = current_cats_map.get(new_role.category_id) if new_role.category_id else None
				if category and category.get("name") != "会員情報" and new_role.permissions != 0:
					raise HTTPException(status_code=403, detail="Member cannot set permissions for new roles outside 会員情報 category")
			else:
				# 既存ロール: permissions 変更は禁止
				if current_role.get("permissions", 0) != new_role.permissions:
					raise HTTPException(status_code=403, detail="Member cannot modify role permissions")

		# member は restricted カテゴリの変更・解除・作成を禁止
		for cat in payload.categories:
			curr_cat = current_cats_map.get(cat.id)
			if curr_cat:
				if curr_cat.get("is_restricted") or curr_cat.get("name") in RESTRICTED_CATEGORY_NAMES:
					if cat.name != curr_cat.get("name") or not cat.is_restricted:
						raise HTTPException(status_code=403, detail=f"Member cannot modify restricted category: {curr_cat.get('name')}")
				elif cat.is_restricted:
					raise HTTPException(status_code=403, detail="Member cannot set category as restricted")
			else:
				if cat.is_restricted or cat.name in RESTRICTED_CATEGORY_NAMES:
					raise HTTPException(status_code=403, detail="Member cannot create restricted category")

		# 削除対象カテゴリの制限チェック
		deleted_cat_ids = set(current_cats_map.keys()) - {c.id for c in payload.categories}
		for d_id in deleted_cat_ids:
			curr_cat = current_cats_map.get(d_id)
			if curr_cat and (curr_cat.get("is_restricted") or curr_cat.get("name") in RESTRICTED_CATEGORY_NAMES):
				raise HTTPException(status_code=403, detail=f"Member cannot delete restricted category: {curr_cat.get('name')}")
	
	await asyncio.to_thread(
		save_manifest,
		[c.model_dump() for c in payload.categories],
		[r.model_dump() for r in payload.roles],
	)
	if payload.role_assignments:
		await asyncio.to_thread(save_role_assignments, payload.role_assignments)
	return payload

RESTRICTED_CATEGORY_NAMES = {"会員情報", "学部学科", "学年"}

@router.patch("/manifest")
async def patch_manifest(payload: ManifestPatch, principal: dict = Depends(require_member)) -> dict:
	"""マニフェスト差分保存。admin と member を許可。"""
	is_admin = principal.get("app_role") == "admin"
	
	if not is_admin:
		current_data = await asyncio.to_thread(fetch_manifest)
		current_cats_map = {cat["id"]: cat for cat in current_data.get("categories", [])}

		# member は restricted カテゴリを変更・作成・解除できない
		for c in payload.upsert_categories:
			curr_cat = current_cats_map.get(c.id)
			if curr_cat:
				# 既存の restricted カテゴリの変更・解除は禁止
				if curr_cat.get("is_restricted") or curr_cat.get("name") in RESTRICTED_CATEGORY_NAMES:
					raise HTTPException(403, f"Member cannot modify restricted category: {curr_cat.get('name')}")
				if c.is_restricted:
					raise HTTPException(403, "Member cannot set admin-only (is_restricted) categories")
			else:
				# 新規作成時
				if c.name in RESTRICTED_CATEGORY_NAMES:
					raise HTTPException(403, f"Member cannot create restricted category: {c.name}")
				if c.is_restricted:
					raise HTTPException(403, "Member cannot create or set admin-only (is_restricted) categories")
		
		# 削除対象の restricted カテゴリ保護
		for d_id in payload.delete_category_ids:
			curr_cat = current_cats_map.get(d_id)
			if curr_cat and (curr_cat.get("is_restricted") or curr_cat.get("name") in RESTRICTED_CATEGORY_NAMES):
				raise HTTPException(403, f"Member cannot delete restricted category: {curr_cat.get('name')}")
		
	await asyncio.to_thread(
		patch_manifest_db,
		[c.model_dump() for c in payload.upsert_categories],
		payload.delete_category_ids,
		[r.model_dump() for r in payload.upsert_roles],
		payload.delete_role_ids,
		payload.upsert_role_assignments,
	)
	return {"ok": True}
