import { auth } from "@/auth";
import { NextResponse } from "next/server";

// 認証が必要なパスのプレフィックス
const MEMBER_ONLY_PATHS = ["/roles", "/admin"];

export default auth((req) => {
	const { pathname } = req.nextUrl;

	const isMemberPath = MEMBER_ONLY_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
	if (!isMemberPath) {
		return NextResponse.next();
	}

	const session = req.auth;
	if (!session) {
		// 未認証: サインインページへ
		const signInUrl = req.nextUrl.clone();
		signInUrl.pathname = "/api/auth/signin";
		signInUrl.searchParams.set("callbackUrl", pathname);
		return NextResponse.redirect(signInUrl);
	}

	// role 確認 (session はカスタム型を通じて any キャストで取得)
	const role = (session as any)?.user?.role as string | undefined;
	const memberRoles = new Set(["member", "admin", "obog"]);

	if (!role || !memberRoles.has(role)) {
		// 非会員: /join にリダイレクト
		const joinUrl = req.nextUrl.clone();
		joinUrl.pathname = "/join";
		return NextResponse.redirect(joinUrl);
	}

	return NextResponse.next();
});

export const config = {
	matcher: ["/roles/:path*", "/admin/:path*"],
};
