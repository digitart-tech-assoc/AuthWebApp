// 役割: 同期実行Action
"use server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

export async function triggerSync(): Promise<{ ok: boolean; bot?: unknown }> {
	const res = await fetch(`${BACKEND_URL}/api/v1/sync`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${SHARED_SECRET}`,
		},
		body: JSON.stringify({ action: "sync_roles" }),
		cache: "no-store",
	});
	const body = (await res.json()) as { ok: boolean; bot?: unknown };
	if (!res.ok) {
		throw new Error("sync failed");
	}
	return body;
}
