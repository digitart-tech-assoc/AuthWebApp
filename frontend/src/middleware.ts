import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PATHS = ["/roles", "/admin"];

export async function middleware(request: NextRequest) {
	let supabaseResponse = NextResponse.next({ request });

	const supabase = createServerClient(
		process.env.NEXT_PUBLIC_SUPABASE_URL!,
		process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
		{
			cookies: {
				getAll() {
					return request.cookies.getAll();
				},
				setAll(cookiesToSet) {
					cookiesToSet.forEach(({ name, value }) =>
						request.cookies.set(name, value),
					);
					supabaseResponse = NextResponse.next({ request });
					cookiesToSet.forEach(({ name, value, options }) =>
						supabaseResponse.cookies.set(name, value, options),
					);
				},
			},
		},
	);

	// セッション检查: 認証状態をリフレッシュ
	const {
		data: { user },
	} = await supabase.auth.getUser();

	const { pathname } = request.nextUrl;
	const isProtected = PROTECTED_PATHS.some(
		(p) => pathname === p || pathname.startsWith(p + "/"),
	);

	if (isProtected && !user) {
		const loginUrl = request.nextUrl.clone();
		loginUrl.pathname = "/login";
		loginUrl.searchParams.set("callbackUrl", pathname);
		return NextResponse.redirect(loginUrl);
	}

	return supabaseResponse;
}

export const config = {
	matcher: [
		"/((?!_next/static|_next/image|favicon.ico|api/auth/callback).*)",
	],
};
