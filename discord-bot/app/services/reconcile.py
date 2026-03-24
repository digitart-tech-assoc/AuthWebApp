"""役割: 差分同期ロジック"""

from __future__ import annotations

import os

import httpx


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


async def run_reconcile() -> dict:
	"""最小同期処理: manifest取得のみ実装。

	本実装ではここで Discord 側との diff を計算して反映する。
	"""
	async with httpx.AsyncClient(timeout=5.0) as client:
		response = await client.get(f"{BACKEND_URL}/api/v1/manifest")
	if response.status_code != 200:
		return {"ok": False, "error": f"manifest fetch failed: {response.status_code}"}
	manifest = response.json()
	return {
		"ok": True,
		"categories": len(manifest.get("categories", [])),
		"roles": len(manifest.get("roles", [])),
	}
