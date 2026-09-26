// 役割: Member専用ロール管理ビュー（個人単位）
// ロール付与/解除はローカルで変更 → 確定時にDB保存+Discord同期を自動実行

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Image from "next/image";
import { fetchMyRoleAssignments, selfBatchRoles } from "@/lib/api/roles";
import { statusBanner, unsavedBar, unsavedBarBtn } from "./roleStyles";

type Category = {
  id: string;
  name: string;
  display_order: number;
  is_collapsed: boolean;
  permissions: number;
  is_restricted: boolean;
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


const catGroupClass = "mb-2.5 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm";
const catHeaderClass = "flex min-h-10 cursor-pointer select-none items-center gap-2 px-4 py-3 transition-colors hover:bg-slate-50";
const catNameClass = "flex-1 text-sm font-semibold text-slate-900";
const catCountClass = "rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500";
const catRoleListClass = "border-t border-slate-100 py-1";
const catRoleItemClass = "flex min-h-10 items-center gap-2.5 px-4 py-1 transition-colors hover:bg-slate-50";
const catRoleItemDisabledClass = `${catRoleItemClass} cursor-not-allowed opacity-40`;
const catRoleNameClass = "flex-1 text-sm text-slate-700";
const roleDotClass = "size-2.5 shrink-0 rounded-full";
const mutedTagClass = "px-2.5 py-1 text-xs text-slate-400";
const pillBtnBase =
  "inline-flex h-8 items-center whitespace-nowrap rounded-full border px-3 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-40";
const assignBtnClass = `${pillBtnBase} border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100`;
const removeRoleBtnClass = `${pillBtnBase} border-red-200 bg-red-50 text-red-700 hover:bg-red-100`;
const chevronClass = (open: boolean) =>
  `size-3.5 shrink-0 text-slate-400 transition-transform ${open ? "rotate-90" : ""}`;

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
      const data = await fetchMyRoleAssignments();
      if (data.assignments) {
        setMembersByRole(data.assignments);
        initialAssignmentsRef.current = JSON.parse(JSON.stringify(data.assignments));
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

  // --- 確定時に自己ロールの付与・解除バッチAPIを呼び出す ---
  async function handleSave() {
    if (!myDiscordId) {
      showStatus({ kind: "error", msg: "Discord ID が特定できません。再ログインしてください。" });
      return;
    }

    setSaveState("saving");
    try {
      const initAssignments = initialAssignmentsRef.current;
      const rolesToAdd: string[] = [];
      const rolesToRemove: string[] = [];

      const allRoleIds = new Set([
        ...Object.keys(membersByRole),
        ...Object.keys(initAssignments),
      ]);

      for (const roleId of allRoleIds) {
        const wasAssigned = (initAssignments[roleId] ?? []).includes(myDiscordId);
        const isAssigned = (membersByRole[roleId] ?? []).includes(myDiscordId);

        if (!wasAssigned && isAssigned) {
          rolesToAdd.push(roleId);
        } else if (wasAssigned && !isAssigned) {
          rolesToRemove.push(roleId);
        }
      }

      if (rolesToAdd.length === 0 && rolesToRemove.length === 0) {
        setHasUnsaved(false);
        setSaveState("idle");
        showStatus({ kind: "info", msg: "変更点はありませんでした" });
        return;
      }

      showStatus({ kind: "info", msg: "ロールの変更を適用中..." });

      // バッチAPIを1回呼び出しで一括更新
      const result = await selfBatchRoles({
        roles_to_add: rolesToAdd,
        roles_to_remove: rolesToRemove,
      });

      if (!result.ok) {
        setSaveState("error");
        showStatus({ kind: "error", msg: `ロール変更に失敗しました: ${result.detail || "エラーが発生しました"}` });
        await fetchMembers();
        return;
      }

      // ベースラインをリセット
      initialAssignmentsRef.current = JSON.parse(JSON.stringify(membersByRole));
      setHasUnsaved(false);
      setSaveState("saved");

      // 全て成功 → ページリロードして最新状態を同期
      window.location.href = `/roles?t=${Date.now()}`;
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


  function hasRole(roleId: string): boolean {
    if (!myDiscordId) return false;
    return (membersByRole[roleId] ?? []).includes(myDiscordId);
  }

  // Pushハンドラは削除（handleSave内で自動実行）

  // My current roles
  const myRoles = sortedRoles.filter((r) => hasRole(r.role_id));

  // ソート: 編集可能カテゴリを先に、次に制限カテゴリ
  const sortedCategories = [...categories].sort((a, b) => {
    const aR = a.is_restricted;
    const bR = b.is_restricted;
    if (aR !== bR) return aR ? 1 : -1;
    return a.display_order - b.display_order;
  });

  const dotColor = (color: string) => (!color || color === "#000000") ? "#d1d5db" : color;

  if (loading) {
    return <div className="p-10 text-center text-sm text-slate-400">読み込み中...</div>;
  }

  return (
    <div className="mx-auto max-w-3xl font-medium">
      {/* Header */}
      <div className="mb-6">
        <h1 className="mb-1 text-2xl font-bold tracking-tight text-slate-900">マイロール</h1>
        <p className="m-0 text-sm text-slate-500">自分のロールを管理できます</p>
      </div>

      {/* Status */}
      {status && (
        <div className={statusBanner(status.kind)}>
          {status.kind === "success" && "✓ "}
          {status.kind === "error" && "✕ "}
          {status.kind === "info" && "ℹ "}
          {status.msg}
        </div>
      )}

      {/* Action bar - PushButtonは自動実行のため非表示 */}

      {/* Profile card */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-3.5">
          <div className="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-full bg-slate-200 text-xl text-slate-500">
            {avatarUrl ? (
              <Image src={avatarUrl} alt={displayName} width={48} height={48} className="size-full object-cover" unoptimized />
            ) : (
              "👤"
            )}
          </div>
          <div>
            <div className="text-base font-bold text-slate-900">{displayName}</div>
            <div className="mt-0.5 text-xs text-slate-500">
              {myDiscordId ? `Discord ID: ${myDiscordId}` : "Discord未連携"}
            </div>
          </div>
        </div>

        <div className="mb-2.5 text-xs font-bold uppercase tracking-wider text-slate-500">現在のロール（{myRoles.length}件）</div>

        {myRoles.length === 0 ? (
          <div className="py-2 text-sm text-slate-400">ロールが割り当てられていません</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {myRoles.map((role) => {
              return (
                <div
                  key={role.role_id}
                  className="inline-flex h-8 items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 pr-2.5 pl-2 text-sm font-medium text-slate-700"
                >
                  <span className={roleDotClass} style={{ backgroundColor: dotColor(role.color) }} />
                  {role.name}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ロールカテゴリ */}
      <div className="mt-6">
        <div className="mb-3 text-base font-bold text-slate-900">ロールカテゴリ</div>

        {sortedCategories.map((cat) => {
          const catRoles = sortedRoles.filter((r) => r.category_id === cat.id);
          if (catRoles.length === 0) return null;
          const isOpen = !collapsedCats.has(cat.id);
          const catRestricted = cat.is_restricted;

          return (
            <div key={cat.id} className={catGroupClass}>
              <div className={catHeaderClass} onClick={() => toggleCat(cat.id)}>
                <svg className={chevronClass(isOpen)} viewBox="0 0 16 16" fill="currentColor">
                  <path d="M5.5 3.5L10.5 8l-5 4.5" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className={catNameClass}>{cat.name}</span>
                <span className={catCountClass}>{catRoles.length}</span>
                {catRestricted && <span className="rounded bg-red-50 px-1.5 py-0.5 text-xs font-semibold text-red-600">管理者専用</span>}
              </div>

              {isOpen && (
                <div className={catRoleListClass}>
                  {catRoles.map((role) => {
                    const assigned = hasRole(role.role_id);
                    const aboveBot = isAboveBot(role);

                    return (
                      <div
                        key={role.role_id}
                        className={aboveBot ? catRoleItemDisabledClass : catRoleItemClass}
                      >
                        <span className={roleDotClass} style={{ backgroundColor: dotColor(role.color) }} />
                        <span className={catRoleNameClass}>{role.name}</span>
                        {aboveBot ? (
                          <span className={mutedTagClass}>編集不可</span>
                        ) : catRestricted ? (
                          <span className={mutedTagClass}>変更不可</span>
                        ) : assigned ? (
                          <button
                            type="button"
                            className={removeRoleBtnClass}
                            disabled={saveState === "saving"}
                            onClick={() => toggleMyRole(role.role_id)}
                          >
                            ✕ 削除
                          </button>
                        ) : (
                          <button
                            type="button"
                            className={assignBtnClass}
                            disabled={saveState === "saving"}
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
        <div className={catGroupClass}>
          <div className={catHeaderClass} onClick={() => toggleCat("__all_roles__")}>
            <svg className={chevronClass(!collapsedCats.has("__all_roles__"))} viewBox="0 0 16 16" fill="currentColor">
              <path d="M5.5 3.5L10.5 8l-5 4.5" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className={catNameClass}>ロール一覧</span>
            <span className={catCountClass}>{sortedRoles.length}</span>
          </div>

          {!collapsedCats.has("__all_roles__") && (
            <div className={catRoleListClass}>
              {sortedRoles.map((role) => {
                const assigned = hasRole(role.role_id);
                const aboveBot = isAboveBot(role);
                return (
                  <div
                    key={role.role_id}
                    className={aboveBot ? catRoleItemDisabledClass : catRoleItemClass}
                  >
                    <span className={roleDotClass} style={{ backgroundColor: dotColor(role.color) }} />
                    <span className={catRoleNameClass}>{role.name}</span>
                    {assigned && <span className={mutedTagClass}>付与済み</span>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Floating save bar */}
      {hasUnsaved && (
        <div className={unsavedBar}>
          <span>未送信の変更があります</span>
          <button
            type="button"
            className={unsavedBarBtn}
            disabled={saveState === "saving"}
            onClick={handleSave}
          >
            {saveState === "saving" ? "処理中..." : "変更を確定"}
          </button>
        </div>
      )}
    </div>
  );
}
