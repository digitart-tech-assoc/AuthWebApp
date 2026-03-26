import "server-only";
import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

type CookieOptions = Parameters<NextResponse["cookies"]["set"]>[2];

type CookieToSet = {
	name: string;
	value: string;
	options?: CookieOptions;
};

export function createSupabaseRouteClient(request: NextRequest) {
	const pendingCookies = new Map<string, CookieToSet>();

	const supabase = createServerClient(
		process.env.NEXT_PUBLIC_SUPABASE_URL!,
		process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
		{
			cookies: {
				getAll() {
					return request.cookies.getAll();
				},
				setAll(cookiesToSet) {
					cookiesToSet.forEach((cookie) => {
						pendingCookies.set(cookie.name, cookie);
						request.cookies.set(cookie.name, cookie.value);
					});
				},
			},
		},
	);

	function applyCookies(response: NextResponse) {
		pendingCookies.forEach(({ name, value, options }) =>
			response.cookies.set(name, value, options),
		);
		return response;
	}

	return { supabase, applyCookies };
}
