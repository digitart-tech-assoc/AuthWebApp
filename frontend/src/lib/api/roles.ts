import type { Member } from "@/types/roles";
import type { ManifestPatchPayload } from "@/components/roles/roleDiff";

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

export interface SelfAssignResponse {
  ok?: boolean;
  detail?: string;
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
 * 自身にロールを付与する
 */
export async function selfAssignRole(roleId: string): Promise<SelfAssignResponse> {
  const res = await fetch("/api/roles/self-assign", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_id: roleId }),
  });
  const data = (await res.json().catch(() => ({}))) as SelfAssignResponse;
  if (!res.ok) {
    return {
      ok: false,
      detail: data.detail || res.statusText,
    };
  }
  return {
    ok: true,
    detail: data.detail,
  };
}

/**
 * 自身からロールを解除する
 */
export async function selfRemoveRole(roleId: string): Promise<SelfAssignResponse> {
  const res = await fetch("/api/roles/self-remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_id: roleId }),
  });
  const data = (await res.json().catch(() => ({}))) as SelfAssignResponse;
  if (!res.ok) {
    return {
      ok: false,
      detail: data.detail || res.statusText,
    };
  }
  return {
    ok: true,
    detail: data.detail,
  };
}
