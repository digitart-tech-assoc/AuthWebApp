import { NextResponse } from "next/server";

import { getBackendAuthorizationHeader, getSessionRole } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

export async function POST() {
	try {
		const role = await getSessionRole();
		const allowed = new Set(["member", "admin", "obog"]);
		if (!allowed.has(role)) {
			return NextResponse.json({ ok: false, detail: "Forbidden" }, { status: 403 });
		}

		const authorization = await getBackendAuthorizationHeader();
		if (!authorization) {
			return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
		}

		const res = await fetchBackend("/api/v1/roles/refresh", {
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
