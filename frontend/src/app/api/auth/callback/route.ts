// 役割: Supabase OAuth コールバック処理

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getBaseUrl } from "@/lib/url";

export async function GET(request: NextRequest) {
	const url = new URL(request.url);
	const qs = url.search || "";
	return NextResponse.redirect(`${getBaseUrl(request)}/auth/callback${qs}`);
}
