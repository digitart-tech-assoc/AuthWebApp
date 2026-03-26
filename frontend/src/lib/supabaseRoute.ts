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
								// Normalize domain option so browser will accept cookie when
								// origin is served as 0.0.0.0 in dev but accessed via localhost
								const opt = cookie.options ? { ...cookie.options } : undefined;
								if (opt && (opt as any).domain === "0.0.0.0") {
									(opt as any).domain = "localhost";
								}
								const normalized = { name: cookie.name, value: cookie.value, options: opt };
								pendingCookies.set(cookie.name, normalized);
								// set on request cookies as well (may be ignored in some contexts)
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
