// 役割: サインアウト

import { createSupabaseRouteClient } from "@/lib/supabaseRoute";
import { getBaseUrl } from "@/lib/url";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
	const { searchParams, origin } = new URL(request.url);
	const callbackUrl = searchParams.get("callbackUrl") ?? "/";
	const { supabase, applyCookies } = createSupabaseRouteClient(request);

	await supabase.auth.signOut();
	const base = getBaseUrl(request);
	return applyCookies(NextResponse.redirect(`${base}${callbackUrl}`));
}
