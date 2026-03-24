// 役割: 同期実行Action
"use server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

export async function triggerSync(): Promise<{ ok: boolean; guild_id?: string; roles?: number }> {
	const res = await fetch(`${BACKEND_URL}/api/v1/roles/refresh`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${SHARED_SECRET}`,
		},
		cache: "no-store",
	});
	const body = (await res.json()) as { ok: boolean; guild_id?: string; roles?: number };
	if (!res.ok) {
		throw new Error("sync failed");
	}
	return body;
}
