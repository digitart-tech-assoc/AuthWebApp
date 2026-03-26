// 役割: マニフェスト操作
"use server";

import { getBackendAuthorizationHeader, getSessionRole } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";
const IS_PROD = process.env.NODE_ENV === "production";

export type ManifestCategory = {
	id: string;
	name: string;
	display_order: number;
	is_collapsed: boolean;
	permissions: number;
};

export type ManifestRole = {
	role_id: string;
	name: string;
	color: string;
	hoist: boolean;
	mentionable: boolean;
	permissions: number;
	position: number;
	category_id: string | null;
};

export type Manifest = {
	categories: ManifestCategory[];
	roles: ManifestRole[];
};

export async function fetchManifest(): Promise<Manifest> {
	const role = await getSessionRole();
	const allowed = new Set(["member", "admin", "obog"]);
	if (!allowed.has(role)) {
		throw new Error("forbidden");
	}

	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	let res = await fetchBackend("/api/v1/manifest", {
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	// 開発環境向けフォールバック: Keycloakトークン検証に失敗した場合のみ再試行する
	if (!res.ok && !IS_PROD && (res.status === 401 || res.status === 403) && SHARED_SECRET) {
		res = await fetchBackend("/api/v1/manifest", {
			headers: { Authorization: `Bearer ${SHARED_SECRET}` },
			cache: "no-store",
		});
	}

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
