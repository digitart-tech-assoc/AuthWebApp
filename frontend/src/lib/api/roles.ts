import type { Member, ManifestPatchPayload } from "@/types/roles";

export interface RoleMembersResponse {
  members?: Member[];
  assignments?: Record<string, string[]>;
}

export interface PushRolesResponse {
  ok?: boolean;
  updated?: number;
  created?: number;
  deleted?: number;
  reordered?: number;
  errors?: string[];
}

export interface RefreshRolesResponse {
  ok?: boolean;
  roles?: number;
}

export interface SelfBatchPayload {
  roles_to_add: string[];
  roles_to_remove: string[];
}

export interface SelfBatchResponse {
  ok?: boolean;
  detail?: string;
  added?: string[];
  removed?: string[];
}

/**
 * ロールに割り当てられているメンバー一覧およびアサイン状態を取得する
 */
export async function fetchRoleMembers(): Promise<RoleMembersResponse> {
  const res = await fetch("/api/roles/members");
  if (!res.ok) {
    throw new Error(`Failed to fetch role members: ${res.statusText}`);
  }
  return res.json();
}

/** ログイン中のユーザー自身に割り当てられたロールを取得する */
export async function fetchMyRoleAssignments(): Promise<RoleMembersResponse> {
  const res = await fetch("/api/roles/me/assignments");
  if (!res.ok) {
    throw new Error(`Failed to fetch my role assignments: ${res.statusText}`);
  }
  return res.json();
}

/**
 * DBへマニフェスト差分を保存する
 */
export async function patchManifest(payload: ManifestPatchPayload): Promise<Response> {
  const res = await fetch("/api/manifest", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res;
}

/**
 * DBのロール設定をDiscordへ同期（プッシュ）する
 */
export async function pushRolesToDiscord(): Promise<PushRolesResponse> {
  const res = await fetch("/api/roles/push", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  const data = (await res.json()) as PushRolesResponse;
  if (!res.ok || !data.ok) {
    return {
      ...data,
      ok: false,
    };
  }
  return data;
}

/**
 * Discordの最新ロール情報をDBへ再取得（リフレッシュ）する
 */
export async function refreshRolesFromDiscord(): Promise<RefreshRolesResponse> {
  const res = await fetch("/api/roles/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  const data = (await res.json()) as RefreshRolesResponse;
  if (!res.ok || !data.ok) {
    return {
      ...data,
      ok: false,
    };
  }
  return data;
}

/**
 * 自身のロールを一括で付与・解除する（バッチ処理）
 */
export async function selfBatchRoles(payload: SelfBatchPayload): Promise<SelfBatchResponse> {
  const res = await fetch("/api/roles/self-batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = (await res.json().catch(() => ({}))) as SelfBatchResponse;
  if (!res.ok) {
    return {
      ok: false,
      detail: data.detail || res.statusText,
    };
  }
  return {
    ok: true,
    added: data.added,
    removed: data.removed,
    detail: data.detail,
  };
}
