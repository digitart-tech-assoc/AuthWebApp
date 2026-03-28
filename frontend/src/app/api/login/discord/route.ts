// 役割: Discord OAuth サインイン開始

import { createSupabaseRouteClient } from "@/lib/supabaseRoute";
import { getBaseUrl } from "@/lib/url";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const callbackUrl = searchParams.get("callbackUrl") ?? "/roles";
	const { supabase, applyCookies } = createSupabaseRouteClient(request);

	// redirectTo は環境変数で上書き可能とする（開発／本番で使い分けるため）
	const envRedirect = process.env.NEXT_PUBLIC_SUPABASE_REDIRECT_URL;
	let redirectBase: string;
	if (envRedirect && envRedirect.trim().length > 0) {
		redirectBase = envRedirect.replace(/\/+$/g, "");
		// 環境変数がベース URL のみ（/api/auth/callback を含まない）だった場合は付与
		if (!redirectBase.includes("/api/auth/callback")) {
			redirectBase = `${redirectBase}/api/auth/callback`;
		}
	} else {
		redirectBase = `${getBaseUrl(request)}/api/auth/callback`;
	}

	const { data, error } = await supabase.auth.signInWithOAuth({
		provider: "discord",
		options: {
			redirectTo: `${redirectBase}?next=${encodeURIComponent(callbackUrl)}`,
		},
	});

	if (error || !data.url) {
		const base = getBaseUrl(request);
		return applyCookies(NextResponse.redirect(`${base}/login?error=oauth_error`));
	}

	// Preserve redirect to Supabase OAuth URL (external)
	return applyCookies(NextResponse.redirect(data.url));
}
