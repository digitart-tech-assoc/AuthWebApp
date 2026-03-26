// 役割: Keycloak ログインルートは Discord ログインへリダイレクト（後方互換）

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
	const formData = await request.formData();
	const callbackValue = formData.get("callbackUrl");
	const callbackUrl =
		typeof callbackValue === "string" && callbackValue.startsWith("/")
			? callbackValue
			: "/roles";
	const { getBaseUrl } = await import("@/lib/url");
	const base = getBaseUrl(request as NextRequest);
	return NextResponse.redirect(
		`${base}/api/login/discord?callbackUrl=${encodeURIComponent(callbackUrl)}`,
	);
}