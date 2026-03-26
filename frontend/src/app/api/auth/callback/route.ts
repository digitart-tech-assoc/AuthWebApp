// 役割: Supabase OAuth コールバック処理

import { createSupabaseRouteClient } from "@/lib/supabaseRoute";
import { getBaseUrl } from "@/lib/url";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

type AuthMeResponse = {
	app_role?: string;
};

type MemberItem = {
	discord_id: string;
};

type MemberListsResponse = {
	pre_member_list?: MemberItem[];
};

function extractDiscordId(user: {
	user_metadata?: Record<string, unknown>;
	identities?: Array<{ identity_data?: Record<string, unknown> }>;
} | null): string | null {
	if (!user) {
		return null;
	}

	const metadata = user.user_metadata ?? {};
	const fromMetadata = metadata.provider_id ?? metadata.sub;
	if (typeof fromMetadata === "string" && fromMetadata.trim().length > 0) {
		return fromMetadata;
	}

	const identities = user.identities ?? [];
	for (const identity of identities) {
		const identityData = identity.identity_data ?? {};
		const candidate = identityData.provider_id ?? identityData.sub;
		if (typeof candidate === "string" && candidate.trim().length > 0) {
			return candidate;
		}
	}

	return null;
}

async function resolvePostSignInPath(accessToken: string, discordId: string | null) {
	try {
		const meRes = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
			headers: { Authorization: `Bearer ${accessToken}` },
			cache: "no-store",
		});

		if (meRes.ok) {
			const me = (await meRes.json()) as AuthMeResponse;
			if (["member", "obog", "admin"].includes(me.app_role ?? "none")) {
				return "/roles";
			}
			if (me.app_role === "pre_member") {
				return "/join/form";
			}
		}

		if (!discordId) {
			return "/non-member";
		}

		const listsRes = await fetch(`${BACKEND_URL}/api/v1/roles/lists`, {
			headers: { Authorization: `Bearer ${accessToken}` },
			cache: "no-store",
		});

		if (!listsRes.ok) {
			return "/non-member";
		}

		const lists = (await listsRes.json()) as MemberListsResponse;
		const preMembers = lists.pre_member_list ?? [];
		const isPreMember = preMembers.some((item) => item.discord_id === discordId);
		return isPreMember ? "/join/form" : "/non-member";
	} catch {
		return "/non-member";
	}
}

export async function GET(request: NextRequest) {
	const { searchParams, origin } = new URL(request.url);
	const code = searchParams.get("code");
	const requestedNext = searchParams.get("next") ?? "/roles";
	const next = requestedNext.startsWith("/") ? requestedNext : "/roles";

	if (code) {
		const { supabase, applyCookies } = createSupabaseRouteClient(request);

		const { error } = await supabase.auth.exchangeCodeForSession(code);
		if (!error) {
			const {
				data: { session },
			} = await supabase.auth.getSession();
			const {
				data: { user },
			} = await supabase.auth.getUser();

			const accessToken = session?.access_token?.trim();
			const discordId = extractDiscordId(user);
			const postSignInPath = accessToken
				? await resolvePostSignInPath(accessToken, discordId)
				: "/login?error=auth_callback_error";

			const needsAccessGate = next === "/roles" || next.startsWith("/roles/") || next === "/admin" || next.startsWith("/admin/");
			const destination = needsAccessGate ? postSignInPath : next;
			const base = getBaseUrl(request);
			return applyCookies(NextResponse.redirect(`${base}${destination}`));
		}
	}

	return NextResponse.redirect(`${origin}/login?error=auth_callback_error`);
}
