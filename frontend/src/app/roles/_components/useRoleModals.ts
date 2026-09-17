"use client";

import { useState, useCallback } from "react";
import type { Role, Category, PermissionTarget, RoleDiffData } from "@/types/roles";

export function useRoleModals(categories: Category[]) {
  // ===== 権限パネル =====
  const [permTarget, setPermTarget] = useState<PermissionTarget | null>(null);

  const openCategoryPermissions = useCallback((cat: Category) => {
    setPermTarget({
      kind: "category",
      id: cat.id,
      name: cat.name,
      currentPermissions: cat.permissions,
    });
  }, []);

  const openRolePermissions = useCallback(
    (role: Role) => {
      const cat = categories.find((c) => c.id === role.category_id);
      setPermTarget({
        kind: "role",
        id: role.role_id,
        name: role.name,
        currentPermissions: role.permissions,
        categoryPermissions: cat?.permissions ?? 0,
        roleDotColor: role.color,
      });
    },
    [categories]
  );

  const closePermissions = useCallback(() => {
    setPermTarget(null);
  }, []);

  // ===== ロール作成・編集モーダル =====
  const [showNewRole, setShowNewRole] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);

  const openNewRoleModal = useCallback(() => {
    setEditingRole(null);
    setShowNewRole(true);
  }, []);

  const openEditRoleModal = useCallback((role: Role) => {
    setEditingRole(role);
    setShowNewRole(true);
  }, []);

  const closeRoleModal = useCallback(() => {
    setShowNewRole(false);
    setEditingRole(null);
  }, []);

  // ===== カテゴリ編集モーダル =====
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);

  const openEditCategoryModal = useCallback((cat: Category) => {
    setEditingCategory(cat);
  }, []);

  const closeEditCategoryModal = useCallback(() => {
    setEditingCategory(null);
  }, []);

  // ===== メンバー管理モーダル =====
  const [memberModalRole, setMemberModalRole] = useState<Role | null>(null);
  const [memberModalReadOnly, setMemberModalReadOnly] = useState(false);

  const openMemberModal = useCallback((role: Role) => {
    setMemberModalReadOnly(false);
    setMemberModalRole(role);
  }, []);

  const openMemberModalReadOnly = useCallback((role: Role) => {
    setMemberModalReadOnly(true);
    setMemberModalRole(role);
  }, []);

  const closeMemberModal = useCallback(() => {
    setMemberModalRole(null);
  }, []);

  // ===== 差分確認モーダル =====
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [diffData, setDiffData] = useState<RoleDiffData | null>(null);

  const openDiffModal = useCallback((data: RoleDiffData) => {
    setDiffData(data);
    setShowDiffModal(true);
  }, []);

  const closeDiffModal = useCallback(() => {
    setShowDiffModal(false);
  }, []);

  return {
    // 権限パネル
    permTarget,
    setPermTarget,
    openCategoryPermissions,
    openRolePermissions,
    closePermissions,

    // ロール作成・編集
    showNewRole,
    setShowNewRole,
    editingRole,
    setEditingRole,
    openNewRoleModal,
    openEditRoleModal,
    closeRoleModal,

    // カテゴリ編集
    editingCategory,
    setEditingCategory,
    openEditCategoryModal,
    closeEditCategoryModal,

    // メンバー管理
    memberModalRole,
    setMemberModalRole,
    memberModalReadOnly,
    openMemberModal,
    openMemberModalReadOnly,
    closeMemberModal,

    // 差分確認
    showDiffModal,
    setShowDiffModal,
    diffData,
    setDiffData,
    openDiffModal,
    closeDiffModal,
  };
}
