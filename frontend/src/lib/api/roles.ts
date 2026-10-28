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
  skipped_members?: number;
  errors?: string[];
}

export interface SelfBatchPayload {
  roles_to_add: string[];
  roles_to_remove: string[];
}

export interface SelfBatchResponse {
  ok?: boolean;
  /** 失敗時の HTTP ステータス。画面の文言はこの値から Frontend で決める（Backend の detail は使わない） */
  status?: number;
  detail?: string;
  added?: string[];
  removed?: string[];
}

export interface SelfCreateRolePayload {
  name: string;
  color: string;
  category_id: string;
}

export interface SelfCreatedRole {
  role_id: string;
  name: string;
  color: string;
  permissions: number;
  position: number;
  category_id: string;
}

export interface SelfCreateRoleResponse {
  ok: boolean;
  /** 失敗時の HTTP ステータス。画面の文言はこの値から Frontend で決める（Backend の detail は使わない） */
  status?: number;
  role?: SelfCreatedRole;
  /** 作成者への付与まで完了したか。false でもロールは作成済み */
  assigned?: boolean;
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
      status: res.status,
    };
  }
  return {
    ok: true,
    added: data.added,
    removed: data.removed,
    detail: data.detail,
  };
}

/**
 * セルフ付与できるカテゴリにロールを作成し、自分に付与する
 */
export async function selfCreateRole(payload: SelfCreateRolePayload): Promise<SelfCreateRoleResponse> {
  const res = await fetch("/api/roles/self-create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = (await res.json().catch(() => ({}))) as SelfCreateRoleResponse;
  if (!res.ok) {
    return { ok: false, status: res.status };
  }
  return { ok: true, role: data.role, assigned: data.assigned };
}
