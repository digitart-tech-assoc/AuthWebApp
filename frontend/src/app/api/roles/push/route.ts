import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

export async function POST() {
	try {
		const res = await fetch(`${BACKEND_URL}/api/v1/roles/push`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${SHARED_SECRET}`,
			},
			cache: "no-store",
		});
		const body = (await res.json()) as {
			ok?: boolean;
			updated?: number;
			created?: number;
			deleted?: number;
			reordered?: number;
			guild_id?: string;
			detail?: string;
		};
		return NextResponse.json(body, { status: res.status });
	} catch {
		return NextResponse.json({ ok: false, detail: "frontend push proxy failed" }, { status: 502 });
	}
}
