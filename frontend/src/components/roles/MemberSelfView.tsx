// 役割: Member専用ロール管理ビュー（個人単位）
// ロール付与/解除はローカルで変更 → 保存 → Discord送信の2ステップ（admin同様）

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import PushButton from "./PushButton";
import styles from "./memberself.module.css";

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

type Status = {
  kind: "success" | "error" | "info";
  msg: string;
};

type Props = {
  categories: Category[];
  roles: Role[];
  myDiscordId: string | null;
  displayName: string;
  avatarUrl: string | null;
};

const RESTRICTED_CATEGORY_NAMES = new Set(["会員情報", "学部学科", "学年"]);

export default function MemberSelfView({ categories, roles, myDiscordId, displayName, avatarUrl }: Props) {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsedCats, setCollapsedCats] = useState<Set<string>>(new Set());

  // --- Role assignment state (batch mode, like admin) ---
  const [membersByRole, setMembersByRole] = useState<Record<string, string[]>>({});
  const initialAssignmentsRef = useRef<Record<string, string[]>>({});
  const [hasUnsaved, setHasUnsaved] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  // Sort roles by position descending (same as Discord hierarchy)
  const sortedRoles = [...roles].sort((a, b) => b.position - a.position);

  // Determine bot role and botPosition for hierarchy constraints
  const botRole = roles.find((r) => r.is_our_bot) ?? roles.find((r) => r.name.toLowerCase() === "bot");
  const botPosition = botRole ? botRole.position : undefined;

  // Fetch all member assignments
  const fetchMembers = useCallback(async () => {
    try {
      const res = await fetch("/api/roles/members");
      if (res.ok) {
        const data = await res.json();
        if (data.assignments) {
          setMembersByRole(data.assignments);
          initialAssignmentsRef.current = JSON.parse(JSON.stringify(data.assignments));
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  function showStatus(s: Status, durationMs = 5000) {
    setStatus(s);
    if (durationMs > 0) {
      setTimeout(() => setStatus(null), durationMs);
    }
  }

  // --- Local toggle (no API call, just state change) ---
  function toggleMyRole(roleId: string) {
    if (!myDiscordId) return;
    setMembersByRole((prev) => {
      const current = new Set(prev[roleId] ?? []);
      if (current.has(myDiscordId)) {
        current.delete(myDiscordId);
      } else {
        current.add(myDiscordId);
      }
      return { ...prev, [roleId]: [...current] };
    });
    setHasUnsaved(true);
    setSaveState("idle");
  }

  // --- Save to DB (same as admin's persistRoles) ---
  async function handleSave() {
    setSaveState("saving");
    try {
      const initAssignments = initialAssignmentsRef.current;
      const upsertRoleAssignments: Record<string, string[]> = {};

      for (const roleId of Object.keys(membersByRole)) {
        const curr = [...membersByRole[roleId]].sort();
        const init = [...(initAssignments[roleId] || [])].sort();
        if (JSON.stringify(curr) !== JSON.stringify(init)) {
          upsertRoleAssignments[roleId] = membersByRole[roleId];
        }
      }

      const hasDiff = Object.keys(upsertRoleAssignments).length > 0;
      if (!hasDiff) {
        setHasUnsaved(false);
        setSaveState("idle");
        showStatus({ kind: "info", msg: "変更点はありませんでした" });
        return;
      }

      const payload = {
        upsert_categories: [],
        delete_category_ids: [],
        upsert_roles: [],
        delete_role_ids: [],
        upsert_role_assignments: upsertRoleAssignments,
      };

      const res = await fetch("/api/manifest", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        setSaveState("error");
        showStatus({ kind: "error", msg: "保存に失敗しました。再度お試しください。" });
        return;
      }

      setHasUnsaved(false);
      setSaveState("saved");
      showStatus({ kind: "success", msg: "変更を保存しました" });
      initialAssignmentsRef.current = JSON.parse(JSON.stringify(membersByRole));
    } catch {
      setSaveState("error");
      showStatus({ kind: "error", msg: "保存に失敗しました。接続を確認してください。" });
    }
  }

  function toggleCat(catId: string) {
    setCollapsedCats((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) next.delete(catId);
      else next.add(catId);
      return next;
    });
  }

  // --- Helpers ---
  function isAboveBot(role: Role): boolean {
    return botPosition !== undefined && role.position >= botPosition;
  }

  function isRestrictedCategory(role: Role): boolean {
    if (!role.category_id) return false;
    const cat = categories.find((c) => c.id === role.category_id);
    return cat ? RESTRICTED_CATEGORY_NAMES.has(cat.name) : false;
  }

  function isRemoveDisabled(role: Role): boolean {
    return isAboveBot(role) || isRestrictedCategory(role);
  }

  function hasRole(roleId: string): boolean {
    if (!myDiscordId) return false;
    return (membersByRole[roleId] ?? []).includes(myDiscordId);
  }

  // Push handlers
  function handlePushSuccess(result: { updated?: number; created?: number; deleted?: number; reordered?: number }) {
    window.location.href = `/roles?pushed=1&updated=${result.updated ?? 0}&created=${result.created ?? 0}&deleted=${result.deleted ?? 0}&reordered=${result.reordered ?? 0}&t=${Date.now()}`;
  }
  function handlePushError(errors?: string[]) {
    showStatus({ kind: "error", msg: errors?.[0] ?? "Discord への送信に失敗しました" });
  }

  // My current roles
  const myRoles = sortedRoles.filter((r) => hasRole(r.role_id));

  // Sort categories: editable first, then restricted (会員情報→学年→学部学科)
  const RESTRICTED_ORDER: Record<string, number> = { "会員情報": 0, "学年": 1, "学部学科": 2 };
  const sortedCategories = [...categories].sort((a, b) => {
    const aR = RESTRICTED_CATEGORY_NAMES.has(a.name);
    const bR = RESTRICTED_CATEGORY_NAMES.has(b.name);
    if (aR !== bR) return aR ? 1 : -1;
    if (aR && bR) return (RESTRICTED_ORDER[a.name] ?? 99) - (RESTRICTED_ORDER[b.name] ?? 99);
    return a.display_order - b.display_order;
  });

  const dotColor = (color: string) => (!color || color === "#000000") ? "#d1d5db" : color;

  if (loading) {
    return <div className={styles.loadingText}>読み込み中...</div>;
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>マイロール</h1>
        <p className={styles.pageSubtitle}>自分のロールを管理できます</p>
      </div>

      {/* Status */}
      {status && (
        <div className={`${styles.statusBanner} ${styles[status.kind]}`}>
          {status.kind === "success" && "✓ "}
          {status.kind === "error" && "✕ "}
          {status.kind === "info" && "ℹ "}
          {status.msg}
        </div>
      )}

      {/* Action bar */}
      <div className={styles.actionBar}>
        <PushButton onSuccess={handlePushSuccess} onError={handlePushError} />
      </div>

      {/* Profile card */}
      <div className={styles.profileCard}>
        <div className={styles.profileHeader}>
          <div className={styles.avatar}>
            {avatarUrl ? (
              <img src={avatarUrl} alt={displayName} />
            ) : (
              "👤"
            )}
          </div>
          <div>
            <div className={styles.profileName}>{displayName}</div>
            <div className={styles.profileSub}>
              {myDiscordId ? `Discord ID: ${myDiscordId}` : "Discord未連携"}
            </div>
          </div>
        </div>

        <div className={styles.sectionLabel}>現在のロール（{myRoles.length}件）</div>

        {myRoles.length === 0 ? (
          <div className={styles.emptyRoles}>ロールが割り当てられていません</div>
        ) : (
          <div className={styles.myRoles}>
            {myRoles.map((role) => {
              return (
                <div
                  key={role.role_id}
                  className={styles.myRoleChip}
                >
                  <span className={styles.roleDot} style={{ backgroundColor: dotColor(role.color) }} />
                  {role.name}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ロールカテゴリ */}
      <div className={styles.catalogSection}>
        <div className={styles.catalogTitle}>ロールカテゴリ</div>

        {sortedCategories.map((cat) => {
          const catRoles = sortedRoles.filter((r) => r.category_id === cat.id);
          if (catRoles.length === 0) return null;
          const isOpen = !collapsedCats.has(cat.id);
          const catRestricted = RESTRICTED_CATEGORY_NAMES.has(cat.name);

          return (
            <div key={cat.id} className={styles.catGroup}>
              <div className={styles.catHeader} onClick={() => toggleCat(cat.id)}>
                <svg className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ""}`} viewBox="0 0 16 16" fill="currentColor">
                  <path d="M5.5 3.5L10.5 8l-5 4.5" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className={styles.catName}>{cat.name}</span>
                <span className={styles.catCount}>{catRoles.length}</span>
                {catRestricted && <span className={styles.catRestricted}>管理者専用</span>}
              </div>

              {isOpen && (
                <div className={styles.catRoleList}>
                  {catRoles.map((role) => {
                    const assigned = hasRole(role.role_id);
                    const aboveBot = isAboveBot(role);

                    return (
                      <div
                        key={role.role_id}
                        className={`${styles.catRoleItem} ${aboveBot ? styles.disabledRole : ""}`}
                      >
                        <span className={styles.roleDot} style={{ backgroundColor: dotColor(role.color) }} />
                        <span className={styles.catRoleName}>{role.name}</span>
                        {aboveBot ? (
                          <span className={styles.alreadyAssigned}>編集不可</span>
                        ) : catRestricted ? (
                          <span className={styles.alreadyAssigned}>変更不可</span>
                        ) : assigned ? (
                          <button
                            type="button"
                            className={styles.removeRoleBtn}
                            onClick={() => toggleMyRole(role.role_id)}
                          >
                            ✕ 削除
                          </button>
                        ) : (
                          <button
                            type="button"
                            className={styles.assignBtn}
                            onClick={() => toggleMyRole(role.role_id)}
                          >
                            ＋ 付与
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* ロール一覧（閲覧のみ） */}
        <div className={styles.catGroup}>
          <div className={styles.catHeader} onClick={() => toggleCat("__all_roles__")}>
            <svg className={`${styles.chevron} ${!collapsedCats.has("__all_roles__") ? styles.chevronOpen : ""}`} viewBox="0 0 16 16" fill="currentColor">
              <path d="M5.5 3.5L10.5 8l-5 4.5" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className={styles.catName}>ロール一覧</span>
            <span className={styles.catCount}>{sortedRoles.length}</span>
          </div>

          {!collapsedCats.has("__all_roles__") && (
            <div className={styles.catRoleList}>
              {sortedRoles.map((role) => {
                const assigned = hasRole(role.role_id);
                const aboveBot = isAboveBot(role);
                return (
                  <div
                    key={role.role_id}
                    className={`${styles.catRoleItem} ${aboveBot ? styles.disabledRole : ""}`}
                  >
                    <span className={styles.roleDot} style={{ backgroundColor: dotColor(role.color) }} />
                    <span className={styles.catRoleName}>{role.name}</span>
                    {assigned && <span className={styles.alreadyAssigned}>付与済み</span>}
                  </div>
                );
              })}
            </div>
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
            onClick={handleSave}
          >
            {saveState === "saving" ? "保存中..." : "保存する"}
          </button>
        </div>
      )}
    </div>
  );
}
