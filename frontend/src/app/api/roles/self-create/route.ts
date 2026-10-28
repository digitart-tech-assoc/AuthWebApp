import { NextResponse } from "next/server";
import { getBackendAuthorizationHeader, getSessionRole } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";
import { hasMemberPrivilege } from "@/lib/permissions";

export async function POST(request: Request) {
	try {
		const role = await getSessionRole();
		if (!hasMemberPrivilege(role)) {
			return NextResponse.json({ ok: false, detail: "Forbidden" }, { status: 403 });
		}

		const authorization = await getBackendAuthorizationHeader();
		if (!authorization) {
			return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
		}

		const payload = await request.json();
		const res = await fetchBackend("/api/v1/roles/self-create", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: authorization,
			},
			body: JSON.stringify(payload),
			cache: "no-store",
		});
		const body = await res.json();
		return NextResponse.json(body, { status: res.status });
	} catch (error) {
		if (error instanceof Error && error.message === "auth-error-401") {
			return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
		}
		if (error instanceof Error && error.message === "auth-error-403") {
			return NextResponse.json({ ok: false, detail: "Forbidden" }, { status: 403 });
		}
		return NextResponse.json({ ok: false, detail: "proxy failed" }, { status: 502 });
	}
}
