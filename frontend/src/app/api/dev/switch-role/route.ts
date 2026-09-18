import { NextResponse } from "next/server";
import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

export async function POST(request: Request) {
	// 開発環境以外では 404 を返して遮断
	if (process.env.NODE_ENV !== "development") {
		return NextResponse.json({ detail: "Not found" }, { status: 404 });
	}

	try {
		const authorization = await getBackendAuthorizationHeader();
		if (!authorization) {
			return NextResponse.json(
				{ detail: "ログインしていません。Discord OAuthでログインしてからロールを切り替えてください。" },
				{ status: 401 },
			);
		}

		const body = await request.json();
		const res = await fetchBackend("/api/v1/dev/switch-role", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: authorization,
			},
			body: JSON.stringify(body),
			cache: "no-store",
		});

		const resBody = await res.json();
		return NextResponse.json(resBody, { status: res.status });
	} catch (error) {
		console.error("[api/dev/switch-role] Proxy error:", error);
		return NextResponse.json({ detail: "Proxy failed" }, { status: 502 });
	}
}
