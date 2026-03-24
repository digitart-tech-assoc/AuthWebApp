import { NextResponse } from "next/server";

import { getBackendAuthorizationHeader } from "@/lib/backendAuth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST() {
	try {
		const authorization = await getBackendAuthorizationHeader();
		if (!authorization) {
			return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
		}

		const res = await fetch(`${BACKEND_URL}/api/v1/roles/refresh`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: authorization,
			},
			cache: "no-store",
		});
		const body = (await res.json()) as { ok?: boolean; guild_id?: string; roles?: number; detail?: string };
		return NextResponse.json(body, { status: res.status });
	} catch {
		return NextResponse.json({ ok: false, detail: "frontend proxy failed" }, { status: 502 });
	}
}
