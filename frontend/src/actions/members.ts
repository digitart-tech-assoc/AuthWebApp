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
