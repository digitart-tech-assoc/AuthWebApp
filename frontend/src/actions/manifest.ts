// 役割: マニフェスト操作
"use server";

import { getBackendAuthorizationHeader, getSessionRole } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";
const IS_PROD = process.env.NODE_ENV === "production";

import type { ManifestCategory, ManifestRole, Manifest } from "@/types/roles";

export async function fetchManifest(): Promise<Manifest> {
	// role 判定はバックエンド側で行う（デュアル判定を避ける）
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetchBackend("/api/v1/manifest", {
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	if (!res.ok) {
		if (res.status === 401) {
			throw new Error("unauthorized");
		}
		if (res.status === 403) {
			throw new Error("forbidden");
		}
		throw new Error(`manifest fetch failed: ${res.status}`);
	}

	return (await res.json()) as Manifest;
}

export async function saveManifest(payload: Manifest): Promise<Manifest> {
	const role = await getSessionRole();
	if (role !== "admin") {
		throw new Error("forbidden");
	}

	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetchBackend("/api/v1/manifest", {
		method: "PUT",
		headers: {
			"Content-Type": "application/json",
			Authorization: authorization,
		},
		body: JSON.stringify(payload),
		cache: "no-store",
	});
	if (!res.ok) {
		throw new Error("manifest save failed");
	}
	return (await res.json()) as Manifest;
}
