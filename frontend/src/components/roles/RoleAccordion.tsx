// 役割: カテゴリアコーディオン（権限エディターパネル統合）

"use client";

import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import RoleList from "./RoleList";
import SyncButton from "./SyncButton";
import PushButton from "./PushButton";
import MembersPanel from "./MembersPanel";
import PermissionEditorPanel, { type PermissionTarget } from "./PermissionEditor";
import NewRoleModal from "./NewRoleModal";
import RoleMemberModal, { type Member } from "./RoleMemberModal";
import styles from "./roles.module.css";

type Category = {
  id: string;
  name: string;
  display_order: number;
  is_collapsed: boolean;
  permissions: number;
};

type Role = {
  role_id: string;
  name: string;
  hoist: boolean;
  mentionable: boolean;
  permissions: number;
  position: number;
  color: string;
  category_id: string | null;
  is_our_bot?: boolean;
};

type Props = {
  categories: Category[];
  roles: Role[];
  accessRole: string;
  myDiscordId?: string | null;
};

type Status = {
  kind: "success" | "error" | "info";
  msg: string;
};

// ===== Icons =====

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg className={`${styles.chevron} ${open ? styles.open : ""}`} viewBox="0 0 16 16" fill="currentColor">
      <path d="M5.5 3.5L10.5 8l-5 4.5" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 1L2 4v4c0 3.5 2.5 6.5 6 7.5C12.5 14.5 14 11.5 14 8V4L8 1z" />
    </svg>
  );
}

// ===== SortableCategoryItem (DnD per category) =====

type SortableCategoryItemProps = {
  cat: Category;
  catRoles: Role[];
  isOpen: boolean;
  isRestrictedCat: boolean;
  memberCanManageCat: boolean;
  isAdmin: boolean;
  isMember: boolean;
  isSelectMode: boolean;
  selectedRoleIds: Set<string>;
  botPosition: number | undefined;
  onToggleCollapse: (id: string) => void;
  onOpenCategoryPermissions: (cat: Category) => void;
  onDeleteCategory: (id: string) => void;
  onToggleSelect: (id: string) => void;
  onReorder: ((ids: string[]) => void) | undefined;
  onOpenRolePermissions: ((role: Role) => void) | undefined;
  onDeleteRole: ((id: string) => void) | undefined;
  onOpenMemberModal: ((role: Role) => void) | undefined;
  styles: Record<string, string>;
};

function SortableCategoryItem({
  cat, catRoles, isOpen, isRestrictedCat, memberCanManageCat,
  isAdmin, isMember, isSelectMode, selectedRoleIds, botPosition,
  onToggleCollapse, onOpenCategoryPermissions, onDeleteCategory,
  onToggleSelect, onReorder, onOpenRolePermissions, onDeleteRole,
  onOpenMemberModal, styles,
}: SortableCategoryItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: cat.id });
  const catStyle = {
    // scaleX/scaleYを1に固定してドラッグ時の引き伸ばしを防ぐ
    transform: CSS.Transform.toString(transform ? { ...transform, scaleX: 1, scaleY: 1 } : null),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={catStyle} className={styles.group}>
      <div
        className={styles.groupHeader}
        onClick={() => onToggleCollapse(cat.id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onToggleCollapse(cat.id); }}
      >
        <ChevronIcon open={isOpen} />
        {/* Drag handle */}
        {(isAdmin || isMember) && (
          <span
            {...attributes}
            {...listeners}
            className={styles.dragHandle}
            title="ドラッグでカテゴリを並び替え"
            onClick={(e) => e.stopPropagation()}
            style={{ cursor: isDragging ? "grabbing" : "grab", padding: "0 4px", lineHeight: 1 }}
          >
            ⠿
          </span>
        )}
        <span className={styles.groupName}>{cat.name}</span>
        <span className={styles.groupCount}>{catRoles.length}</span>

        {isAdmin ? (
          <button
            type="button"
            className={styles.catPermBtn}
            onClick={(e) => { e.stopPropagation(); onOpenCategoryPermissions(cat); }}
            title="カテゴリ権限設定"
            aria-label={`${cat.name} の権限設定`}
          >
            <ShieldIcon />
            権限
          </button>
        ) : null}

        {/* member: ロールが残っている場合は削除不可。admin: 制限なし */}
        {isAdmin ? (
          <button
            type="button"
            className={styles.groupDeleteBtn}
            onClick={(e) => { e.stopPropagation(); onDeleteCategory(cat.id); }}
            aria-label={`${cat.name} を削除`}
            title="カテゴリを削除"
          >
            ✕
          </button>
        ) : memberCanManageCat ? (
          <button
            type="button"
            className={`${styles.groupDeleteBtn} ${catRoles.length > 0 ? styles.btnDisabled ?? "" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              if (catRoles.length > 0) return;
              onDeleteCategory(cat.id);
            }}
            disabled={catRoles.length > 0}
            aria-label={`${cat.name} を削除`}
            title={catRoles.length > 0
              ? `カテゴリ内のロール（${catRoles.length}件）をすべて削除してからカテゴリを削除できます`
              : "カテゴリを削除"
            }
          >
            ✕
          </button>
        ) : null}
      </div>

      {isOpen && (
        <RoleList
          roles={catRoles}
          showHeader={false}
          selectedIds={isSelectMode ? selectedRoleIds : undefined}
          onToggleSelect={isSelectMode ? onToggleSelect : undefined}
          onReorder={!isSelectMode && isAdmin ? onReorder : undefined}
          onPermissions={!isSelectMode && isAdmin ? onOpenRolePermissions : undefined}
          onDelete={!isSelectMode && (isAdmin || memberCanManageCat) ? onDeleteRole : undefined}
          onMembers={!isSelectMode && (isAdmin || memberCanManageCat) ? onOpenMemberModal : undefined}
          botPosition={botPosition}
        />
      )}
    </div>
  );
}

// ===== Component =====

export default function RoleAccordion({ categories: initCategories, roles: initRoles, accessRole, myDiscordId = null }: Props) {
  const [query, setQuery] = useState("");
  const [allRoles, setAllRoles] = useState<Role[]>([]);
  const [localCategories, setLocalCategories] = useState<Category[]>([]);
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set());
  const [hasUnsaved, setHasUnsaved] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  // Selection (category creation mode)
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");

  // Status banner
  const [status, setStatus] = useState<Status | null>(null);
  const statusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ===== Permission panel =====
  const [permTarget, setPermTarget] = useState<PermissionTarget | null>(null);

  // ===== New role modal =====
  const [showNewRole, setShowNewRole] = useState(false);

  // ===== Member management =====
  const [allMembers, setAllMembers] = useState<Member[]>([]);
  const [membersByRole, setMembersByRole] = useState<Record<string, string[]>>({});
  const [memberModalRole, setMemberModalRole] = useState<Role | null>(null);
  const [memberModalReadOnly, setMemberModalReadOnly] = useState(false);
  const [baseMembersByRole, setBaseMembersByRole] = useState<Record<string, string[]>>({});

  // ===== Diff modal =====
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [diffData, setDiffData] = useState<{ roleAdded: { role: Role, memberCount: number }[], memberAssigned: { roleId: string, roleName: string, added: string[], removed: string[] }[], permissionEdited: { roleId: string, roleName: string, oldPermissions: string, newPermissions: string }[], orderChanged: { roleId: string, roleName: string, oldPosition: number, newPosition: number }[], roleDeleted: Role[], categoriesAdded: Category[], categoriesDeleted: Category[] } | null>(null);
  const [pendingRoles, setPendingRoles] = useState<Role[] | null>(null);
  const [pendingCats, setPendingCats] = useState<Category[] | null>(null);
  
  // Store initial values for diff calculation
  const [baseRoles, setBaseRoles] = useState<Role[]>(initRoles);
  const [baseCategories, setBaseCategories] = useState<Category[]>(initCategories);

  const isAdmin = accessRole === "admin";
  const isMember = accessRole === "member";
  const canCreateRole = ["admin", "member", "obog"].includes(accessRole);
  const canCreateCategory = isAdmin || isMember;
  const canManageMembers = isAdmin;
  const canEditManifest = isAdmin || isMember;

  // memberモードでロール付与を禁止するカテゴリ名
  const RESTRICTED_CATEGORY_NAMES = new Set(["\u4f1a\u54e1\u60c5\u5831", "\u5b66\u90e8\u5b66\u79d1", "\u5b66\u5e74"]);

  function showStatus(s: Status, durationMs = 5000) {
    setStatus(s);
    if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
    if (durationMs > 0) {
      statusTimerRef.current = setTimeout(() => setStatus(null), durationMs);
    }
  }

  useEffect(() => {
    const sortedRoles = initRoles.slice().sort((a, b) => b.position - a.position);
    const categoriesWithPerms = initCategories.map(c => ({ ...c, permissions: c.permissions ?? 0 }));
    
    setAllRoles(sortedRoles);
    setLocalCategories(categoriesWithPerms);
    setBaseRoles(initRoles);
    setBaseCategories(initCategories);
    setHasUnsaved(false);
    setSaveState("idle");
    setSelectedRoleIds(new Set());
    setIsSelectMode(false);
    setNewCategoryName("");
    setPermTarget(null);
  }, [initRoles, initCategories]);

  const fetchMembers = useCallback(async () => {
    try {
      const res = await fetch("/api/roles/members");
      if (res.ok) {
        const data = await res.json();
        if (data.members) setAllMembers(data.members);
        if (data.assignments) {
          setMembersByRole(data.assignments);
          setBaseMembersByRole(JSON.parse(JSON.stringify(data.assignments))); // Deep copy
        }
      }
    } catch (e) {
      console.error("Failed to fetch members", e);
    }
  }, []);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  const normalizedQuery = query.trim().toLowerCase();
  const filteredRoles = useMemo(() => {
    if (!normalizedQuery) return allRoles;
    return allRoles.filter((r) => r.name.toLowerCase().includes(normalizedQuery));
  }, [allRoles, normalizedQuery]);

  // DnD sensors for category reorder
  const useCatDndSensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // ===== Diff calculation =====
  function calculateDifferences(nextRoles: Role[], nextCats: Category[]) {
    // Roles
    const nextRoleIds = new Set(nextRoles.map(r => r.role_id));
    const baseRoleIds = new Set(baseRoles.map(r => r.role_id));
    
    const addedRoles = nextRoles.filter(r => !baseRoleIds.has(r.role_id));
    const deletedRoles = baseRoles.filter(r => !nextRoleIds.has(r.role_id));
    
    // Separate changed roles into permission, order, and member changes
    const permissionEdited: { roleId: string, roleName: string, oldPermissions: string, newPermissions: string }[] = [];
    const orderChanged: { roleId: string, roleName: string, oldPosition: number, newPosition: number }[] = [];
    
    for (const nextRole of nextRoles) {
      if (!baseRoleIds.has(nextRole.role_id)) continue;
      const baseRole = baseRoles.find(r => r.role_id === nextRole.role_id)!;
      
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
    
    // Member assignments: separate added roles vs existing roles
    const roleAdded: { role: Role, memberCount: number }[] = addedRoles.map(r => ({
      role: r,
      memberCount: (membersByRole[r.role_id] || []).length,
    }));
    
    const memberAssigned: { roleId: string, roleName: string, added: string[], removed: string[] }[] = [];
    const baseRoleMap = new Map(baseRoles.map(r => [r.role_id, r.name]));
    
    for (const roleId of baseRoleIds) {
      const baseMemberIds = baseMembersByRole[roleId] || [];
      const nextMemberIds = membersByRole[roleId] || [];
      
      const baseMemberSet = new Set(baseMemberIds);
      const nextMemberSet = new Set(nextMemberIds);
      
      const addedMembers = nextMemberIds.filter(m => !baseMemberSet.has(m));
      const removedMembers = baseMemberIds.filter(m => !nextMemberSet.has(m));
      
      if (addedMembers.length > 0 || removedMembers.length > 0) {
        memberAssigned.push({
          roleId,
          roleName: baseRoleMap.get(roleId) || roleId,
          added: addedMembers,
          removed: removedMembers,
        });
      }
    }
    
    // Categories
    const nextCatIds = new Set(nextCats.map(c => c.id));
    const baseCatIds = new Set(baseCategories.map(c => c.id));
    
    const categoriesAdded = nextCats.filter(c => !baseCatIds.has(c.id));
    const categoriesDeleted = baseCategories.filter(c => !nextCatIds.has(c.id));

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

  // ===== Persist (with diff confirmation) =====
  async function persistRoles(nextRoles: Role[], nextCats: Category[]) {
    // Calculate differences
    const diff = calculateDifferences(nextRoles, nextCats);
    setDiffData(diff);
    setPendingRoles(nextRoles);
    setPendingCats(nextCats);
    setShowDiffModal(true);
  }

  // ===== Execute save (called after diff confirmation) =====
  async function executeSave() {
    if (!pendingRoles || !pendingCats) return;
    
    setShowDiffModal(false);
    setSaveState("saving");
    try {
      const res = await fetch("/api/manifest", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ categories: pendingCats, roles: pendingRoles, role_assignments: membersByRole }),
      });
      if (!res.ok) {
        setSaveState("error");
        showStatus({ kind: "error", msg: "保存に失敗しました。再度お試しください。" });
        setPendingRoles(null);
        setPendingCats(null);
        return;
      }
      setHasUnsaved(false);
      setSaveState("saved");
      showStatus({ kind: "success", msg: "変更を保存しました" });
      setPendingRoles(null);
      setPendingCats(null);
    } catch {
      setSaveState("error");
      showStatus({ kind: "error", msg: "保存に失敗しました。接続を確認してください。" });
      setPendingRoles(null);
      setPendingCats(null);
    }
  }

  // ===== Reorder =====
  function reorderGroup(orderedRoleIds: string[]) {
    const targetIds = new Set(orderedRoleIds);
    const roleMap = new Map(allRoles.map((r) => [r.role_id, r]));
    const reorderedGroup = orderedRoleIds.map((id) => roleMap.get(id)).filter((r): r is Role => Boolean(r));
    if (reorderedGroup.length !== orderedRoleIds.length) return;
    let pointer = 0;
    const reordered = allRoles.map((r) => {
      if (!targetIds.has(r.role_id)) return r;
      return reorderedGroup[pointer++];
    });
    const total = reordered.length;
    const withPos = reordered.map((r, i) => ({ ...r, position: total - i }));
    setAllRoles(withPos);
    setHasUnsaved(true);
    setSaveState("idle");
  }

  // ===== Accordion =====
  function toggleCollapse(id: string) {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // ===== Selection / Category creation =====
  function toggleSelectMode() {
    setIsSelectMode((v) => !v);
    setSelectedRoleIds(new Set());
    setNewCategoryName("");
  }

  function toggleSelectRole(id: string) {
    setSelectedRoleIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function createCategory() {
    const name = newCategoryName.trim();
    if (!name) return;
    const newCatId = `cat_${Date.now()}`;
    const newCat: Category = { id: newCatId, name, display_order: localCategories.length, is_collapsed: false, permissions: 0 };
    const updatedRoles = allRoles.map((r) => selectedRoleIds.has(r.role_id) ? { ...r, category_id: newCatId } : r);
    const nextCats = [...localCategories, newCat];
    setLocalCategories(nextCats);
    setAllRoles(updatedRoles);
    setSelectedRoleIds(new Set());
    setIsSelectMode(false);
    setNewCategoryName("");
    setHasUnsaved(true);
    setSaveState("idle");
    showStatus({ kind: "info", msg: `カテゴリ「${name}」を作成しました（保存ボタンで確定）` });
  }

  function deleteCategory(catId: string) {
    // 削除確認ダイアログ
    const category = localCategories.find(c => c.id === catId);
    if (!confirm(`カテゴリ「${category?.name}」を削除してもよろしいですか？`)) {
      return;
    }
    
    const nextCats = localCategories.filter((c) => c.id !== catId);
    setLocalCategories(nextCats);
    // Uncategorize roles (don't delete them)
    setAllRoles((prev) => prev.map((r) => r.category_id === catId ? { ...r, category_id: null } : r));
    setHasUnsaved(true);
    setSaveState("idle");
    showStatus({ kind: "info", msg: "カテゴリを削除しました。属していたロールは「未分類」に移動しました（保存ボタンで確定）" });
  }

  function deleteRole(roleId: string) {
    // 削除確認ダイアログ
    const role = allRoles.find(r => r.role_id === roleId);
    if (!confirm(`ロール「${role?.name}」を削除してもよろしいですか？`)) {
      return;
    }
    
    // member がロール削除する場合、割り当てられたメンバーがいないか確認
    if (isMember) {
      const assignedMembers = membersByRole[roleId] || [];
      if (assignedMembers.length > 0) {
        showStatus({ kind: "error", msg: `ロール削除失敗: このロールに${assignedMembers.length}人のメンバーが割り当てられています。先にメンバーを解除してください。` });
        return;
      }
    }
    
    setAllRoles((prev) => prev.filter((r) => r.role_id !== roleId));
    setHasUnsaved(true);
    setSaveState("idle");
    showStatus({ kind: "info", msg: "ロールを削除しました（保存ボタンで確定）" });
  }

  // カテゴリの並び替え（DnD完了時）
  function reorderCategories(oldIndex: number, newIndex: number) {
    setLocalCategories((prev) => {
      const next = arrayMove(prev, oldIndex, newIndex);
      return next.map((c, i) => ({ ...c, display_order: i }));
    });
    setHasUnsaved(true);
    setSaveState("idle");
  }

  // ===== SyncButton / PushButton =====
  function handleSyncSuccess(count: number) {
    // Rely on page reload to fetch the new member data via useEffect on the fresh mount
    window.location.href = `/roles?synced=1&roles=${count}&t=${Date.now()}`;
  }
  function handleSyncError() {
    showStatus({ kind: "error", msg: "Discord からの取得に失敗しました" });
  }
  function handlePushSuccess(result: { updated?: number; created?: number; deleted?: number; reordered?: number }) {
    const parts: string[] = [];
    if (result.updated) parts.push(`更新 ${result.updated}`);
    if (result.created) parts.push(`作成 ${result.created}`);
    if (result.deleted) parts.push(`削除 ${result.deleted}`);
    if (result.reordered) parts.push(`並び替え ${result.reordered}`);
    const detail = parts.length ? `（${parts.join(" / ")}）` : "";
    window.location.href = `/roles?pushed=1&updated=${result.updated ?? 0}&created=${result.created ?? 0}&deleted=${result.deleted ?? 0}&reordered=${result.reordered ?? 0}&t=${Date.now()}`;
  }
  function handlePushError(errors?: string[]) {
    if (errors && errors.length > 0) {
      showStatus({ kind: "error", msg: `Discord への送信エラー: ${errors[0]}` });
    } else {
      showStatus({ kind: "error", msg: "Discord への送信に失敗しました" });
    }
  }

  // ===== Permission panel callbacks =====
  const openCategoryPermissions = useCallback((cat: Category) => {
    setPermTarget({
      kind: "category",
      id: cat.id,
      name: cat.name,
      currentPermissions: cat.permissions,
    });
  }, []);

  const openRolePermissions = useCallback((role: Role) => {
    const cat = localCategories.find((c) => c.id === role.category_id);
    setPermTarget({
      kind: "role",
      id: role.role_id,
      name: role.name,
      currentPermissions: role.permissions,
      categoryPermissions: cat?.permissions ?? 0,
      roleDotColor: role.color,
    });
  }, [localCategories]);

  function handlePermissionSave(newPermissions: number) {
    if (!permTarget) return;
    if (permTarget.kind === "category") {
      // 1. Update the category's permissions
      setLocalCategories((prev) =>
        prev.map((c) => c.id === permTarget.id ? { ...c, permissions: newPermissions } : c)
      );
      // 2. AUTO-SYNC: propagate to all roles in this category
      setAllRoles((prev) =>
        prev.map((r) => r.category_id === permTarget.id ? { ...r, permissions: newPermissions } : r)
      );
      showStatus({ kind: "info", msg: `カテゴリ「${permTarget.name}」の権限をカテゴリ内ロールに適用しました（保存ボタンで確定）` });
    } else {
      setAllRoles((prev) =>
        prev.map((r) => r.role_id === permTarget.id ? { ...r, permissions: newPermissions } : r)
      );
      showStatus({ kind: "info", msg: `ロール「${permTarget.name}」の権限を更新しました（保存ボタンで確定）` });
    }
    setHasUnsaved(true);
    setSaveState("idle");
    setPermTarget(null);
  }

  // ===== New Role creation callback =====
  function handleRoleCreated(role: {
    role_id: string; name: string; color: string;
    hoist: boolean; mentionable: boolean; permissions: number;
    position: number; category_id: string | null; is_our_bot?: boolean;
  }) {
    // Assign the new role a position that places it at the bottom of editable roles.
    // Editable roles are those below botPosition (or all roles if no bot found).
    // Discord positions: higher number = higher in hierarchy. 0 = @everyone.
    // We want lowest editable position = 1 (just above @everyone).
    const editableRoles = botPosition !== undefined
      ? allRoles.filter((r) => r.position < botPosition)
      : allRoles;
    const lowestEditablePos = editableRoles.length > 0
      ? Math.min(...editableRoles.map((r) => r.position))
      : 1;
    // Place new role one below the current minimum to put it at the bottom
    const newPos = Math.max(1, lowestEditablePos - 1);
    const roleWithPos = { ...role, position: newPos };
    setAllRoles((prev) => [...prev, roleWithPos]);
    setShowNewRole(false);
    showStatus({ kind: "success", msg: `ロール「${role.name}」を作成しました！（保存ボタンで確定）` });
    // Mark as unsaved so the manifest can be persisted with the new role
    setHasUnsaved(true);
    setSaveState("idle");
  }

  // ===== Member management callbacks =====
  const handleOpenMemberModal = useCallback((role: Role) => {
    setMemberModalReadOnly(false);
    setMemberModalRole(role);
  }, []);

  // ロール一覧用: 閉覧のみで開く
  const handleOpenMemberModalReadOnly = useCallback((role: Role) => {
    setMemberModalReadOnly(true);
    setMemberModalRole(role);
  }, []);

  function handleMemberCommit(roleId: string, add: string[], remove: string[]) {
    setMembersByRole((prev) => {
      const current = new Set(prev[roleId] ?? []);
      add.forEach((id) => current.add(id));
      remove.forEach((id) => current.delete(id));
      return { ...prev, [roleId]: [...current] };
    });
    setMemberModalRole(null);
    setHasUnsaved(true);
    setSaveState("idle");
    const detail = `付与 ${add.length}名 / 削除 ${remove.length}名`;
    showStatus({ kind: "success", msg: `メンバー割り当てを変更しました（${detail}）（保存ボタンで確定）` });
  }

  // ===== Self-assign (member mode) =====
  const handleSelfAssign = useCallback(async (role: Role) => {
    // 禁止カテゴリチェック
    const cat = localCategories.find((c) => c.id === role.category_id);
    if (cat && RESTRICTED_CATEGORY_NAMES.has(cat.name)) {
      showStatus({ kind: "error", msg: `「${cat.name}」カテゴリのロールは付与できません` });
      return;
    }
    try {
      const res = await fetch("/api/roles/self-assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_id: role.role_id }),
      });
      const data = await res.json();
      if (!res.ok) {
        showStatus({ kind: "error", msg: data.detail ?? "ロールの付与に失敗しました" });
        return;
      }
      showStatus({ kind: "success", msg: `ロール「${role.name}」を自分に付与しました` });
    } catch {
      showStatus({ kind: "error", msg: "ロールの付与に失敗しました。接続を確認してください" });
    }
  }, [localCategories, RESTRICTED_CATEGORY_NAMES]);

  const categoryIds = new Set(localCategories.map((c) => c.id));
  const uncategorizedRoles = filteredRoles.filter((r) => !r.category_id || !categoryIds.has(r.category_id));

  // Determine the bot role: prefer is_our_bot flag, fall back to name 'bot' as a safety net
  const botRole = allRoles.find((r) => r.is_our_bot) ?? allRoles.find((r) => r.name.toLowerCase() === "bot");
  const botPosition = botRole ? botRole.position : undefined;
  const botPermissions = botRole ? BigInt(botRole.permissions) : 0n;

  return (
    <div className={styles.page}>
      {/* Page header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>ロール管理</h1>
        <p className={styles.pageSubtitle}>Discord サーバーのロールとカテゴリ、権限を管理できます</p>
      </div>

      {/* Status banner */}
      {status && (
        <div className={`${styles.statusBanner} ${styles[status.kind]}`}>
          {status.kind === "success" && "✓ "}
          {status.kind === "error" && "✕ "}
          {status.kind === "info" && "ℹ "}
          {status.msg}
        </div>
      )}

      {/* Top action bar */}
      <div className={styles.topBar}>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}>⌕</span>
          <input
            type="search"
            className={styles.search}
            placeholder="ロールを検索..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <SyncButton onSuccess={handleSyncSuccess} onError={handleSyncError} />
        {(isAdmin || isMember) ? <PushButton onSuccess={handlePushSuccess} onError={handlePushError} /> : null}
        {canCreateRole ? (
          <button type="button" className={styles.btnCreate} onClick={() => setShowNewRole(true)}>
            + ロール作成
          </button>
        ) : null}
        <button
          type="button"
          className={isSelectMode ? styles.btnDanger : styles.btnSecondary}
          onClick={toggleSelectMode}
          disabled={!canCreateCategory}
          title={canCreateCategory ? "カテゴリ作成" : "カテゴリ作成は admin/member のみ可能"}
        >
          {isSelectMode ? "戻る" : "⊙ カテゴリ作成"}
        </button>
      </div>

      <div className={`${styles.statusBanner} ${styles.info}`}>
        {isAdmin
          ? "adminモード: すべての管理操作が有効です。"
          : isMember
          ? "memberモード: ロール・カテゴリの作成および自分へのロール付与ができます。会員全体のロール管理は無効です。"
          : "obogモード: ロール作成のみ可能です。"}
      </div>

      {/* Category creation selection bar */}
      {isSelectMode && (
        <div className={styles.selectionBar}>
          <span className={styles.selectionBarLabel}>
            チェックしたロールをカテゴリに追加します（選択数: {selectedRoleIds.size}）
          </span>
          <input
            type="text"
            className={styles.categoryNameInput}
            placeholder="カテゴリ名を入力"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") createCategory(); }}
          />
          <button type="button" className={styles.btnPrimary} onClick={createCategory}
            disabled={!newCategoryName.trim()}>
            作成
          </button>
        </div>
      )}

      {/* Role board */}
      <div className={styles.board}>

        {/* ===== Categorized groups with DnD reordering ===== */}
        <DndContext
          sensors={useCatDndSensors}
          collisionDetection={closestCenter}
          onDragEnd={(event: DragEndEvent) => {
            const { active, over } = event;
            if (!over || active.id === over.id) return;
            const oldIdx = localCategories.findIndex((c) => c.id === active.id);
            const newIdx = localCategories.findIndex((c) => c.id === over.id);
            if (oldIdx !== -1 && newIdx !== -1) reorderCategories(oldIdx, newIdx);
          }}
        >
          <SortableContext items={localCategories.map((c) => c.id)} strategy={verticalListSortingStrategy}>
            {localCategories.map((cat) => {
              const catRoles = filteredRoles.filter((r) => r.category_id === cat.id);
              const isOpen = !collapsedIds.has(cat.id);
              const isRestrictedCat = RESTRICTED_CATEGORY_NAMES.has(cat.name);
              const memberCanManageCat = isMember && !isRestrictedCat;
              return (
                <SortableCategoryItem
                  key={cat.id}
                  cat={cat}
                  catRoles={catRoles}
                  isOpen={isOpen}
                  isRestrictedCat={isRestrictedCat}
                  memberCanManageCat={memberCanManageCat}
                  isAdmin={isAdmin}
                  isMember={isMember}
                  isSelectMode={isSelectMode}
                  selectedRoleIds={selectedRoleIds}
                  botPosition={botPosition}
                  onToggleCollapse={toggleCollapse}
                  onOpenCategoryPermissions={openCategoryPermissions}
                  onDeleteCategory={deleteCategory}
                  onToggleSelect={toggleSelectRole}
                  onReorder={!isSelectMode && isAdmin ? reorderGroup : undefined}
                  onOpenRolePermissions={!isSelectMode && isAdmin ? openRolePermissions : undefined}
                  onDeleteRole={!isSelectMode && (isAdmin || memberCanManageCat) ? deleteRole : undefined}
                  onOpenMemberModal={!isSelectMode && (isAdmin || memberCanManageCat) ? handleOpenMemberModal : undefined}
                  styles={styles}
                />
              );
            })}
          </SortableContext>
        </DndContext>

        {/* ===== Master All Roles ===== */}
        <div className={styles.group}>
          <div
            className={styles.groupHeader}
            onClick={() => toggleCollapse("__all_roles__")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") toggleCollapse("__all_roles__"); }}
          >
            <ChevronIcon open={!collapsedIds.has("__all_roles__")} />
            <span className={styles.groupName}>ロール一覧</span>
            <span className={styles.groupCount}>{filteredRoles.length}</span>
          </div>
          {!collapsedIds.has("__all_roles__") && (
            <RoleList
              roles={filteredRoles}
              showHeader={false}
              selectedIds={isSelectMode ? selectedRoleIds : undefined}
              onToggleSelect={isSelectMode ? toggleSelectRole : undefined}
              onReorder={!isSelectMode && isAdmin ? reorderGroup : undefined}
              onPermissions={!isSelectMode && isAdmin ? openRolePermissions : undefined}
              onDelete={!isSelectMode && isAdmin ? deleteRole : undefined}
              onMembers={
                !isSelectMode && (isAdmin || isMember)
                  ? handleOpenMemberModalReadOnly
                  : undefined
              }
              botPosition={botPosition}
            />
          )}
        </div>
      </div>

      {/* Floating save bar */}
      {hasUnsaved && (
        <div className={styles.unsavedBar}>
          <span>未保存の変更があります</span>
          <button
            type="button"
            className={styles.unsavedBarBtn}
            disabled={saveState === "saving" || !canEditManifest}
            onClick={() => persistRoles(allRoles, localCategories)}
          >
            {saveState === "saving" ? "保存中..." : canEditManifest ? "保存する" : "保存不可"}
          </button>
        </div>
      )}

      {/* Permission editor panel */}
      {permTarget && (
        <PermissionEditorPanel
          target={permTarget}
          botPermissions={botPermissions}
          onSave={handlePermissionSave}
          onClose={() => setPermTarget(null)}
        />
      )}

      {/* New role modal */}
      {showNewRole && (
        <NewRoleModal
          categories={localCategories}
          botPermissions={botPermissions}
          onCreated={handleRoleCreated}
          onClose={() => setShowNewRole(false)}
          isMember={isMember}
          restrictedCategoryNames={RESTRICTED_CATEGORY_NAMES}
        />
      )}

      {/* Member management modal */}
      {memberModalRole && (
        <RoleMemberModal
          roleName={memberModalRole.name}
          roleId={memberModalRole.role_id}
          allMembers={allMembers}
          currentMemberIds={membersByRole[memberModalRole.role_id] ?? []}
          onCommit={(add, remove) => handleMemberCommit(memberModalRole.role_id, add, remove)}
          onClose={() => setMemberModalRole(null)}
          isLocked={botPosition !== undefined && memberModalRole.position >= botPosition}
          readOnly={memberModalReadOnly}
          selfDiscordId={(!memberModalReadOnly && isMember) ? myDiscordId : null}
        />
      )}

      {/* Members management panel */}
      {canManageMembers ? (
        <MembersPanel />
      ) : (
        <div className={styles.lockedPanel}>
          会員情報カテゴリの操作・会員管理は admin のみ利用できます。
        </div>
      )}

      {/* Diff confirmation modal */}
      {showDiffModal && diffData && (
        <>
          <div className={styles.overlay} onClick={() => setShowDiffModal(false)} />
          <div className={styles.modal} role="dialog" aria-label="変更内容確認">
            <div className={styles.header}>
              <p className={styles.title}>変更内容の確認</p>
              <p className={styles.subtitle}>以下の変更を保存します</p>
            </div>
            <div style={{ maxHeight: '400px', overflowY: 'auto', padding: '20px', fontSize: '14px' }}>
              {(diffData.roleAdded.length > 0 || diffData.memberAssigned.length > 0 || diffData.permissionEdited.length > 0 || diffData.orderChanged.length > 0 || diffData.roleDeleted.length > 0 || diffData.categoriesAdded.length > 0 || diffData.categoriesDeleted.length > 0) ? (
                <>
                  {diffData.roleAdded.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#10b981', marginBottom: '8px' }}>
                        ＋ ロールを追加（{diffData.roleAdded.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.roleAdded.map(item => (
                          <li key={item.role.role_id}>
                            <strong>{item.role.name}</strong>
                            {item.memberCount > 0 && <div style={{ marginLeft: '12px', color: '#6b7280', fontSize: '12px' }}>👥 {item.memberCount}名割り当て</div>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {diffData.memberAssigned.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#8b5cf6', marginBottom: '8px' }}>
                        👥 メンバーを割り当て（{diffData.memberAssigned.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.memberAssigned.map(change => (
                          <li key={change.roleId}>
                            <strong>{change.roleName}</strong>
                            {change.added.length > 0 && <div style={{ marginLeft: '12px', color: '#10b981' }}>➕ {change.added.length}名追加</div>}
                            {change.removed.length > 0 && <div style={{ marginLeft: '12px', color: '#ef4444' }}>➖ {change.removed.length}名削除</div>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {diffData.permissionEdited.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#f59e0b', marginBottom: '8px' }}>
                        🔒 権限を編集（{diffData.permissionEdited.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.permissionEdited.map(item => (
                          <li key={item.roleId}>
                            <strong>{item.roleName}</strong>
                            <div style={{ marginLeft: '12px', color: '#6b7280', fontSize: '12px' }}>
                              {item.oldPermissions} → {item.newPermissions}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {diffData.orderChanged.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#3b82f6', marginBottom: '8px' }}>
                        📍 表示する順番を変更（{diffData.orderChanged.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.orderChanged.map(item => (
                          <li key={item.roleId}>
                            <strong>{item.roleName}</strong>
                            <div style={{ marginLeft: '12px', color: '#6b7280', fontSize: '12px' }}>
                              位置: {item.oldPosition} → {item.newPosition}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {diffData.roleDeleted.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#ef4444', marginBottom: '8px' }}>
                        ✕ ロール削除（{diffData.roleDeleted.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.roleDeleted.map(r => (
                          <li key={r.role_id}>{r.name}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {diffData.categoriesAdded.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#10b981', marginBottom: '8px' }}>
                        ＋ カテゴリ追加（{diffData.categoriesAdded.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.categoriesAdded.map(c => (
                          <li key={c.id}>{c.name}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {diffData.categoriesDeleted.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', color: '#ef4444', marginBottom: '8px' }}>
                        ✕ カテゴリ削除（{diffData.categoriesDeleted.length}件）
                      </div>
                      <ul style={{ margin: '0 0 0 20px', paddingLeft: '0' }}>
                        {diffData.categoriesDeleted.map(c => (
                          <li key={c.id}>{c.name}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p style={{ color: '#6b7280' }}>変更がありません</p>
              )}
            </div>
            <div style={{ display: 'flex', gap: '12px', padding: '20px', borderTop: '1px solid #e5e7eb' }}>
              <button
                type="button"
                style={{
                  flex: 1,
                  padding: '8px 16px',
                  border: '1px solid #d1d5db',
                  background: 'white',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px',
                }}
                onClick={() => setShowDiffModal(false)}
              >
                キャンセル
              </button>
              <button
                type="button"
                style={{
                  flex: 1,
                  padding: '8px 16px',
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold',
                }}
                onClick={executeSave}
              >
                保存する
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
