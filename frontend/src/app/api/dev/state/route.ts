import { NextResponse } from "next/server";
import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

export async function GET() {
	// 開発環境以外では 404 を返して遮断
	if (process.env.NODE_ENV !== "development") {
		return NextResponse.json({ detail: "Not found" }, { status: 404 });
	}

	try {
		const authorization = await getBackendAuthorizationHeader();
		if (!authorization) {
			// 未ログインの場合はエラーにせず、none 状態として返す
			return NextResponse.json({
				discord_id: null,
				current_role: "none",
				is_paid: false,
				available_roles: ["admin", "member", "none", "obog", "pre_member", "sub_user"],
			});
		}

		const res = await fetchBackend("/api/v1/dev/state", {
			headers: { Authorization: authorization },
			cache: "no-store",
		});

		const body = await res.json();
		return NextResponse.json(body, { status: res.status });
	} catch (error) {
		console.error("[api/dev/state] Proxy error:", error);
		return NextResponse.json({ detail: "Proxy failed" }, { status: 502 });
	}
}
