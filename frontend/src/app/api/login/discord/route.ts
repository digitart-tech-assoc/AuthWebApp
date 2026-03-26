// 役割: Discord OAuth サインイン開始

import { createSupabaseRouteClient } from "@/lib/supabaseRoute";
import { getBaseUrl } from "@/lib/url";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
	const { searchParams, origin } = new URL(request.url);
	const callbackUrl = searchParams.get("callbackUrl") ?? "/roles";
	const { supabase, applyCookies } = createSupabaseRouteClient(request);

	const { data, error } = await supabase.auth.signInWithOAuth({
		provider: "discord",
		options: {
			redirectTo: `${origin}/api/auth/callback?next=${encodeURIComponent(callbackUrl)}`,
		},
	});

	if (error || !data.url) {
		const base = getBaseUrl(request);
		return applyCookies(NextResponse.redirect(`${base}/login?error=oauth_error`));
	}

	// Preserve redirect to Supabase OAuth URL (external)
	return applyCookies(NextResponse.redirect(data.url));
}
