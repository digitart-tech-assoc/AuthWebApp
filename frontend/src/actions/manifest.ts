// 役割: マニフェスト操作
"use server";

import { getBackendAuthorizationHeader } from "@/lib/backendAuth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export type ManifestCategory = {
	id: string;
	name: string;
	display_order: number;
	is_collapsed: boolean;
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
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(`${BACKEND_URL}/api/v1/manifest`, {
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	if (!res.ok) {
		if (res.status === 401) {
			throw new Error("unauthorized");
		}
		throw new Error(`manifest fetch failed: ${res.status}`);
	}

	return (await res.json()) as Manifest;
}

export async function saveManifest(payload: Manifest): Promise<Manifest> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(`${BACKEND_URL}/api/v1/manifest`, {
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
