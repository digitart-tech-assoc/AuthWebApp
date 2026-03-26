// 役割: カテゴリアコーディオン（権限エディターパネル統合）

"use client";

import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import RoleList from "./RoleList";
import SyncButton from "./SyncButton";
import PushButton from "./PushButton";
import PermissionEditorPanel, { type PermissionTarget } from "./PermissionEditor";
import NewRoleModal from "./NewRoleModal";
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
};

type Props = {
  categories: Category[];
  roles: Role[];
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

// ===== Component =====

export default function RoleAccordion({ categories: initCategories, roles: initRoles }: Props) {
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

  function showStatus(s: Status, durationMs = 5000) {
    setStatus(s);
    if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
    if (durationMs > 0) {
      statusTimerRef.current = setTimeout(() => setStatus(null), durationMs);
    }
  }

  useEffect(() => {
    setAllRoles(initRoles.slice().sort((a, b) => b.position - a.position));
    setLocalCategories(initCategories.map(c => ({ ...c, permissions: c.permissions ?? 0 })));
    setHasUnsaved(false);
    setSaveState("idle");
    setSelectedRoleIds(new Set());
    setIsSelectMode(false);
    setNewCategoryName("");
    setPermTarget(null);
  }, [initRoles, initCategories]);

  const normalizedQuery = query.trim().toLowerCase();
  const filteredRoles = useMemo(() => {
    if (!normalizedQuery) return allRoles;
    return allRoles.filter((r) => r.name.toLowerCase().includes(normalizedQuery));
  }, [allRoles, normalizedQuery]);

  // ===== Persist =====
  async function persistRoles(nextRoles: Role[], nextCats: Category[]) {
    setSaveState("saving");
    try {
      const res = await fetch("/api/manifest", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ categories: nextCats, roles: nextRoles }),
      });
      if (!res.ok) {
        setSaveState("error");
        showStatus({ kind: "error", msg: "保存に失敗しました。再度お試しください。" });
        return;
      }
      setHasUnsaved(false);
      setSaveState("saved");
      showStatus({ kind: "success", msg: "変更を保存しました" });
    } catch {
      setSaveState("error");
      showStatus({ kind: "error", msg: "保存に失敗しました。接続を確認してください。" });
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
    if (!name || selectedRoleIds.size === 0) return;
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
    const nextCats = localCategories.filter((c) => c.id !== catId);
    setLocalCategories(nextCats);
    setAllRoles((prev) => prev.filter((r) => r.category_id !== catId));
    setHasUnsaved(true);
    setSaveState("idle");
    showStatus({ kind: "info", msg: "カテゴリとそれに含まれるロールを削除しました（保存ボタンで確定）" });
  }

  function deleteRole(roleId: string) {
    setAllRoles((prev) => prev.filter((r) => r.role_id !== roleId));
    setHasUnsaved(true);
    setSaveState("idle");
    showStatus({ kind: "info", msg: "ロールを削除しました（保存ボタンで確定）" });
  }

  // ===== SyncButton / PushButton =====
  function handleSyncSuccess(count: number) {
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
    setAllRoles((prev) => [...prev, role]);
    setShowNewRole(false);
    showStatus({ kind: "success", msg: `ロール「${role.name}」を作成しました！（保存ボタンで確定）` });
    // Mark as unsaved so the manifest can be persisted with the new role
    setHasUnsaved(true);
    setSaveState("idle");
  }

  const categoryIds = new Set(localCategories.map((c) => c.id));
  const uncategorizedRoles = filteredRoles.filter((r) => !r.category_id || !categoryIds.has(r.category_id));

  // Determine the highest position of the bot role to prevent editing roles above it
  const botRole = allRoles.find((r) => r.is_our_bot);
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
        <PushButton onSuccess={handlePushSuccess} onError={handlePushError} />
        <button type="button" className={styles.btnCreate} onClick={() => setShowNewRole(true)}>
          + ロール作成
        </button>
        <button type="button" className={isSelectMode ? styles.btnDanger : styles.btnSecondary} onClick={toggleSelectMode}>
          {isSelectMode ? "戻る" : "⊙ カテゴリ作成"}
        </button>
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
            disabled={!newCategoryName.trim() || selectedRoleIds.size === 0}>
            作成
          </button>
        </div>
      )}

      {/* Role board */}
      <div className={styles.board}>

        {/* ===== Categorized groups ===== */}
        {localCategories.map((cat) => {
          const catRoles = filteredRoles.filter((r) => r.category_id === cat.id);
          if (catRoles.length === 0 && !isSelectMode) return null;
          const isOpen = !collapsedIds.has(cat.id);

          return (
            <div key={cat.id} className={styles.group}>
              <div
                className={styles.groupHeader}
                onClick={() => toggleCollapse(cat.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") toggleCollapse(cat.id); }}
              >
                <ChevronIcon open={isOpen} />
                <span className={styles.groupName}>{cat.name}</span>
                <span className={styles.groupCount}>{catRoles.length}</span>

                {/* Category permissions button */}
                <button
                  type="button"
                  className={styles.catPermBtn}
                  onClick={(e) => { e.stopPropagation(); openCategoryPermissions(cat); }}
                  title="カテゴリ権限設定"
                  aria-label={`${cat.name} の権限設定`}
                >
                  <ShieldIcon />
                  権限
                </button>

                {/* Delete button */}
                <button
                  type="button"
                  className={styles.groupDeleteBtn}
                  onClick={(e) => { e.stopPropagation(); deleteCategory(cat.id); }}
                  aria-label={`${cat.name} を削除`}
                  title="カテゴリを削除"
                >
                  ✕
                </button>
              </div>

              {isOpen && (
                <RoleList
                  roles={catRoles}
                  showHeader={false}
                  selectedIds={isSelectMode ? selectedRoleIds : undefined}
                  onToggleSelect={isSelectMode ? toggleSelectRole : undefined}
                  onReorder={!isSelectMode ? reorderGroup : undefined}
                  onPermissions={!isSelectMode ? openRolePermissions : undefined}
                  onDelete={!isSelectMode ? deleteRole : undefined}
                  botPosition={botPosition}
                />
              )}
            </div>
          );
        })}

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
              onReorder={!isSelectMode ? reorderGroup : undefined}
              onPermissions={!isSelectMode ? openRolePermissions : undefined}
              onDelete={!isSelectMode ? deleteRole : undefined}
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
            disabled={saveState === "saving"}
            onClick={() => persistRoles(allRoles, localCategories)}
          >
            {saveState === "saving" ? "保存中..." : "保存する"}
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
        />
      )}
    </div>
  );
}
