import type { Role, Category, RoleDiffData, ManifestPatchPayload } from "@/types/roles";
export type { ManifestPatchPayload };

/**
 * 初期状態（ベース）と現在の変更状態を比較し、モーダル表示用の差分オブジェクトを生成する
 */
export function calculateDifferences(
  nextRoles: Role[],
  baseRoles: Role[],
  nextCats: Category[],
  baseCategories: Category[],
  membersByRole: Record<string, string[]>,
  baseMembersByRole: Record<string, string[]>
): RoleDiffData {
  const nextRoleIds = new Set(nextRoles.map((r) => r.role_id));
  const baseRoleIds = new Set(baseRoles.map((r) => r.role_id));

  const addedRoles = nextRoles.filter((r) => !baseRoleIds.has(r.role_id));
  const deletedRoles = baseRoles.filter((r) => !nextRoleIds.has(r.role_id));

  // ロールの権限変更・順序変更の検知
  const permissionEdited: { roleId: string; roleName: string; oldPermissions: string; newPermissions: string }[] = [];
  const orderChanged: { roleId: string; roleName: string; oldPosition: number; newPosition: number }[] = [];

  for (const nextRole of nextRoles) {
    if (!baseRoleIds.has(nextRole.role_id)) continue;
    const baseRole = baseRoles.find((r) => r.role_id === nextRole.role_id)!;

    if (baseRole.permissions !== nextRole.permissions) {
      permissionEdited.push({
        roleId: nextRole.role_id,
        roleName: nextRole.name,
        oldPermissions: String(baseRole.permissions || "0"),
        newPermissions: String(nextRole.permissions || "0"),
      });
    }

    if (baseRole.position !== nextRole.position) {
      orderChanged.push({
        roleId: nextRole.role_id,
        roleName: nextRole.name,
        oldPosition: baseRole.position,
        newPosition: nextRole.position,
      });
    }
  }

  // メンバー割り当て変更の検知
  const roleAdded: { role: Role; memberCount: number }[] = addedRoles.map((r) => ({
    role: r,
    memberCount: (membersByRole[r.role_id] || []).length,
  }));

  const memberAssigned: { roleId: string; roleName: string; added: string[]; removed: string[] }[] = [];
  const baseRoleMap = new Map(baseRoles.map((r) => [r.role_id, r.name]));

  for (const roleId of baseRoleIds) {
    const baseMemberIds = baseMembersByRole[roleId] || [];
    const nextMemberIds = membersByRole[roleId] || [];

    const baseMemberSet = new Set(baseMemberIds);
    const nextMemberSet = new Set(nextMemberIds);

    const addedMembers = nextMemberIds.filter((m) => !baseMemberSet.has(m));
    const removedMembers = baseMemberIds.filter((m) => !nextMemberSet.has(m));

    if (addedMembers.length > 0 || removedMembers.length > 0) {
      memberAssigned.push({
        roleId,
        roleName: baseRoleMap.get(roleId) || roleId,
        added: addedMembers,
        removed: removedMembers,
      });
    }
  }

  // カテゴリ変更の検知
  const nextCatIds = new Set(nextCats.map((c) => c.id));
  const baseCatIds = new Set(baseCategories.map((c) => c.id));

  const categoriesAdded = nextCats.filter((c) => !baseCatIds.has(c.id));
  const categoriesDeleted = baseCategories.filter((c) => !nextCatIds.has(c.id));

  return {
    roleAdded,
    memberAssigned,
    permissionEdited,
    orderChanged,
    roleDeleted: deletedRoles,
    categoriesAdded,
    categoriesDeleted,
  };
}

/**
 * バックエンド（PATCH /api/manifest）に送信する差分ペイロードを構築する
 */
export function buildManifestPatchPayload(
  pendingRoles: Role[],
  baseRoles: Role[],
  pendingCats: Category[],
  baseCategories: Category[],
  membersByRole: Record<string, string[]>,
  initialAssignments: Record<string, string[]>
): { payload: ManifestPatchPayload; hasDiff: boolean } {
  const upsertCategories = pendingCats.filter((c) => {
    const init = baseCategories.find((i) => i.id === c.id);
    return !init || JSON.stringify(init) !== JSON.stringify(c);
  });
  const deleteCatIds = baseCategories.filter((c) => !pendingCats.find((n) => n.id === c.id)).map((c) => c.id);

  const upsertRoles = pendingRoles.filter((r) => {
    const init = baseRoles.find((i) => i.role_id === r.role_id);
    return !init || JSON.stringify(init) !== JSON.stringify(r);
  });
  const deleteRoleIds = baseRoles.filter((r) => !pendingRoles.find((n) => n.role_id === r.role_id)).map((r) => r.role_id);

  const upsertRoleAssignments: Record<string, string[]> = {};
  for (const roleId of Object.keys(membersByRole)) {
    const curr = [...(membersByRole[roleId] || [])].sort();
    const init = [...(initialAssignments[roleId] || [])].sort();
    if (JSON.stringify(curr) !== JSON.stringify(init)) {
      upsertRoleAssignments[roleId] = membersByRole[roleId];
    }
  }

  const payload: ManifestPatchPayload = {
    upsert_categories: upsertCategories,
    delete_category_ids: deleteCatIds,
    upsert_roles: upsertRoles,
    delete_role_ids: deleteRoleIds,
    upsert_role_assignments: upsertRoleAssignments,
  };

  const hasDiff =
    upsertCategories.length > 0 ||
    deleteCatIds.length > 0 ||
    upsertRoles.length > 0 ||
    deleteRoleIds.length > 0 ||
    Object.keys(upsertRoleAssignments).length > 0;

  return { payload, hasDiff };
}
