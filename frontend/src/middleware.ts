import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PATHS = ["/roles", "/admin"];

export async function middleware(request: NextRequest) {
	let supabaseResponse = NextResponse.next({ request });

	try {
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
			// middleware では絶対URLが必須
			const origin = new URL(request.url).origin;
			const loginUrl = new URL(`${origin}/login`);
			loginUrl.searchParams.set("callbackUrl", pathname);
			return NextResponse.redirect(loginUrl);
		}

		return supabaseResponse;
	} catch (error) {
		console.error("Middleware error:", error);
		// エラーの場合は次のリクエストに進める
		return supabaseResponse;
	}
}

export const config = {
	matcher: [
		"/((?!_next/static|_next/image|favicon.ico|api/auth/callback).*)",
	],
};
