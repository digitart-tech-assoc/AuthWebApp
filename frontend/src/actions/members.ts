// 役割: メンバーリスト同期アクション

"use server";

import { getBackendAuthorizationHeader } from "@/lib/backendAuth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export interface MemberListResponse {
	ok: boolean;
	guild_id: string;
	member_list: number;
	admin_list: number;
	pre_member_list: number;
}

export interface MemberItem {
	discord_id: string;
	user_id: string | null;
	assigned_at: string | null;
}

export interface MemberListsData {
	member_list: MemberItem[];
	admin_list: MemberItem[];
	pre_member_list: MemberItem[];
}

export interface PreMember {
	discord_id: string;
	user_id: string | null;
	assigned_at: string | null;
	supabase_user_id: string | null;
}

export interface AddMemberResponse {
	ok: boolean;
	data: {
		discord_id: string;
		added_to_member_list: boolean;
		created_at: string | null;
	};
}

export interface PaidInvitationResponse {
	ok: boolean;
	data: {
		discord_id: string;
		created: boolean;
		created_at: string | null;
	};
}

/**
 * Discord からメンバーリストを同期
 */
export async function syncMembers(): Promise<MemberListResponse> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(`${BACKEND_URL}/api/v1/roles/members/sync`, {
		method: "POST",
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	if (res.status === 401 || res.status === 403) {
		throw new Error(`auth-error-${res.status}`);
	}

	if (!res.ok) {
		const error = await res.text();
		throw new Error(`sync failed: ${res.status} - ${error}`);
	}

	return (await res.json()) as MemberListResponse;
}

/**
 * メンバーリストを取得
 */
export async function getMembers(): Promise<MemberListsData> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(`${BACKEND_URL}/api/v1/roles/lists`, {
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	if (res.status === 401 || res.status === 403) {
		throw new Error(`auth-error-${res.status}`);
	}

	if (!res.ok) {
		const error = await res.text();
		throw new Error(`fetch failed: ${res.status} - ${error}`);
	}

	return (await res.json()) as MemberListsData;
}

/**
 * Pre-member list を取得（検索オプション付き）
 */
export async function getPreMemberList(search?: string): Promise<PreMember[]> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const url = new URL("/api/v1/members/pre_member/list", BACKEND_URL);
	if (search) {
		url.searchParams.append("search", search);
	}

	const res = await fetch(url.toString(), {
		method: "GET",
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	if (res.status === 401 || res.status === 403) {
		throw new Error(`auth-error-${res.status}`);
	}

	if (!res.ok) {
		const error = await res.text();
		throw new Error(`fetch failed: ${res.status} - ${error}`);
	}

	const data = await res.json();
	return data.data || [];
}

/**
 * Pre-member を member_list に追加
 */
export async function addMember(
	discordId: string,
	note?: string
): Promise<AddMemberResponse> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(`${BACKEND_URL}/api/v1/members/member/add`, {
		method: "POST",
		headers: {
			Authorization: authorization,
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			discord_id: discordId,
			note: note || null,
		}),
		cache: "no-store",
	});

	if (res.status === 401 || res.status === 403) {
		throw new Error(`auth-error-${res.status}`);
	}

	if (!res.ok) {
		const error = await res.text();
		throw new Error(`add failed: ${res.status} - ${error}`);
	}

	return (await res.json()) as AddMemberResponse;
}

/**
 * 入会費支払い済みユーザーを paid_invitations に登録
 */
export async function registerPaidInvitation(
	discordId: string,
	note?: string
): Promise<PaidInvitationResponse> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(
		`${BACKEND_URL}/api/v1/members/paid_invitation/register`,
		{
			method: "POST",
			headers: {
				Authorization: authorization,
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				discord_id: discordId,
				note: note || null,
			}),
			cache: "no-store",
		}
	);

	if (res.status === 401 || res.status === 403) {
		throw new Error(`auth-error-${res.status}`);
	}

	if (!res.ok) {
		const error = await res.text();
		throw new Error(`registration failed: ${res.status} - ${error}`);
	}

	return (await res.json()) as PaidInvitationResponse;
}
