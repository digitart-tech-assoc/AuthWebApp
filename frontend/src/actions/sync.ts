// 役割: 同期実行Action
"use server";

import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

export async function triggerSync(): Promise<{ ok: boolean; guild_id?: string; roles?: number }> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetchBackend("/api/v1/roles/refresh", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: authorization,
		},
		cache: "no-store",
	});
	const body = (await res.json()) as { ok: boolean; guild_id?: string; roles?: number };
	if (!res.ok) {
		throw new Error("sync failed");
	}
	return body;
}
