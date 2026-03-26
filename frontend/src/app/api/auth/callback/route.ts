// 役割: Supabase OAuth コールバック処理

import { createSupabaseRouteClient } from "@/lib/supabaseRoute";
import { getBaseUrl } from "@/lib/url";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
	const { searchParams, origin } = new URL(request.url);
	const code = searchParams.get("code");
	const requestedNext = searchParams.get("next") ?? "/roles";
	const next = requestedNext.startsWith("/") ? requestedNext : "/roles";

	if (code) {
		const { supabase, applyCookies } = createSupabaseRouteClient(request);

		const { error } = await supabase.auth.exchangeCodeForSession(code);
		if (!error) {
			const base = getBaseUrl(request);
			return applyCookies(NextResponse.redirect(`${base}${next}`));
		}
	}

	return NextResponse.redirect(`${origin}/login?error=auth_callback_error`);
}
