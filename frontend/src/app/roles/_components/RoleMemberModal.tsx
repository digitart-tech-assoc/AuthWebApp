// 役割: ロールメンバー管理モーダル（付与・削除）

"use client";

import { useState, useMemo } from "react";
import Image from "next/image";
import ModalFrame from "./ModalFrame";
import { btnDanger, btnPrimary, btnSecondary, modalCloseBtn, modalHeader, modalSubtitle, modalTitle, textInput } from "./roleStyles";

import type { Member } from "@/types/roles";
export type { Member };

type Props = {
  roleName: string;
  roleId: string;
  allMembers: Member[];
  /** 現在このロールを持つメンバーのuser_idセット */
  currentMemberIds: string[];
  isLocked?: boolean;
  /** trueの場合：閉覧のみ（付与・削除ボタン非表示） */
  readOnly?: boolean;
  onCommit: (add: string[], remove: string[]) => void;
  onClose: () => void;
  /** 設定時: このユーザーのみ操作可（memberモード用） */
  selfDiscordId?: string | null;
};

type Screen = "list" | "grant" | "revoke";

const headerClass = `${modalHeader} border-b border-slate-200 pb-3`;
const searchWrapClass = "shrink-0 px-4 pt-3 pb-2";
const memberListClass = "min-h-0 flex-1 overflow-y-auto px-2 py-1.5";
const memberRowBaseClass =
  "flex min-h-10 select-none items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors";
const memberRowClass = `${memberRowBaseClass} cursor-pointer hover:bg-slate-100`;
const memberRowDisabledClass = `${memberRowBaseClass} cursor-default opacity-50`;
const checkboxClass = "size-4 shrink-0 cursor-pointer accent-blue-600 disabled:cursor-default";
const memberNameClass = "min-w-0 flex-1 truncate text-sm font-medium text-slate-700";
const badgeClass = "shrink-0 rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500";
const lockedBadgeClass = "shrink-0 rounded-md bg-slate-500 px-1.5 py-0.5 text-xs text-white";
const emptyClass = "py-6 text-center text-sm text-slate-500";
const footerClass =
  "flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-6 py-4";
const lockedMsgClass = "inline-flex items-center gap-1 text-xs font-medium text-slate-500";


function MemberAvatar({ member }: { member: Member }) {
  const avatarUrl = member.avatar
    ? `https://cdn.discordapp.com/avatars/${member.user_id}/${member.avatar}.webp?size=32`
    : `https://cdn.discordapp.com/embed/avatars/${Number(member.user_id) % 5}.png`;
  return (
    <Image
      src={avatarUrl}
      alt={member.display_name || member.username}
      className="size-8 shrink-0 rounded-full object-cover"
      width={32}
      height={32}
      unoptimized
      onError={(e) => {
        (e.target as HTMLImageElement).src = `https://cdn.discordapp.com/embed/avatars/0.png`;
      }}
    />
  );
}

export default function RoleMemberModal({
  roleName,
  allMembers,
  currentMemberIds,
  isLocked,
  readOnly = false,
  onCommit,
  onClose,
  selfDiscordId = null,
}: Props) {
  const [screen, setScreen] = useState<Screen>("list");
  // ローカルの付与済みセット（コミットするまで反映しない）
  const [localMemberIds, setLocalMemberIds] = useState<Set<string>>(
    new Set(currentMemberIds)
  );
  const [selectedForGrant, setSelectedForGrant] = useState<Set<string>>(new Set());
  const [selectedForRevoke, setSelectedForRevoke] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");

  const currentMembers = useMemo(
    () => allMembers.filter((m) => localMemberIds.has(m.user_id)),
    [allMembers, localMemberIds]
  );

  const filteredAll = useMemo(() => {
    const q = search.toLowerCase();
    return allMembers.filter(
      (m) =>
        (m.display_name ?? m.username).toLowerCase().includes(q) ||
        m.username.toLowerCase().includes(q)
    );
  }, [allMembers, search]);

  function confirmGrant() {
    setLocalMemberIds((prev) => {
      const next = new Set(prev);
      selectedForGrant.forEach((id) => next.add(id));
      return next;
    });
    setSelectedForGrant(new Set());
    setScreen("list");
  }

  function confirmRevoke() {
    setLocalMemberIds((prev) => {
      const next = new Set(prev);
      selectedForRevoke.forEach((id) => next.delete(id));
      return next;
    });
    setSelectedForRevoke(new Set());
    setScreen("list");
  }

  function handleCommit() {
    const original = new Set(currentMemberIds);
    const add = [...localMemberIds].filter((id) => !original.has(id));
    const remove = [...original].filter((id) => !localMemberIds.has(id));
    onCommit(add, remove);
  }

  const hasChanges =
    JSON.stringify([...localMemberIds].sort()) !== JSON.stringify([...currentMemberIds].sort());

  // ── Screen: 付与相手を選ぶ ──
  if (screen === "grant") {
    return (
      <ModalFrame onBackdropClick={() => setScreen("list")}>
        <div className={headerClass}>
          <span className={modalTitle}>ロールを付与するメンバーを選択</span>
          <button type="button" className={modalCloseBtn} onClick={() => setScreen("list")}>✕</button>
        </div>
        <div className={searchWrapClass}>
          <input
            className={textInput}
            placeholder="名前で検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className={memberListClass}>
          {filteredAll.map((m) => {
            const alreadyHas = localMemberIds.has(m.user_id);
            const checked = selectedForGrant.has(m.user_id);
            const isSelfOnly = selfDiscordId !== null && m.user_id !== selfDiscordId;
            return (
              <label
                key={m.user_id}
                className={alreadyHas || isSelfOnly ? memberRowDisabledClass : memberRowClass}
              >
                <input
                  type="checkbox"
                  className={checkboxClass}
                  disabled={alreadyHas || isSelfOnly}
                  checked={checked}
                  onChange={() => {
                    if (alreadyHas || isSelfOnly) return;
                    setSelectedForGrant((prev) => {
                      const next = new Set(prev);
                      if (next.has(m.user_id)) next.delete(m.user_id);
                      else next.add(m.user_id);
                      return next;
                    });
                  }}
                />
                <MemberAvatar member={m} />
                <span className={memberNameClass}>{m.display_name || m.username}</span>
                {alreadyHas && <span className={badgeClass}>付与済</span>}
                {!alreadyHas && isSelfOnly && <span className={lockedBadgeClass}>操作不可</span>}
              </label>
            );
          })}
        </div>
        <div className={footerClass}>
          <button type="button" className={btnSecondary} onClick={() => setScreen("list")}>
            戻る
          </button>
          <button
            type="button"
            className={btnPrimary}
            onClick={confirmGrant}
            disabled={selectedForGrant.size === 0}
          >
            決定 ({selectedForGrant.size}名)
          </button>
        </div>
      </ModalFrame>
    );
  }

  // ── Screen: 削除相手を選ぶ ──
  if (screen === "revoke") {
    const filteredCurrent = currentMembers.filter((m) => {
      const q = search.toLowerCase();
      return (
        (m.display_name ?? m.username).toLowerCase().includes(q) ||
        m.username.toLowerCase().includes(q)
      );
    });
    return (
      <ModalFrame onBackdropClick={() => setScreen("list")}>
        <div className={headerClass}>
          <span className={modalTitle}>ロールを削除するメンバーを選択</span>
          <button type="button" className={modalCloseBtn} onClick={() => setScreen("list")}>✕</button>
        </div>
        <div className={searchWrapClass}>
          <input
            className={textInput}
            placeholder="名前で検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className={memberListClass}>
          {filteredCurrent.length === 0 && (
            <p className={emptyClass}>このロールを持つメンバーはいません</p>
          )}
          {filteredCurrent.map((m) => {
            const checked = selectedForRevoke.has(m.user_id);
            const isSelfOnly = selfDiscordId !== null && m.user_id !== selfDiscordId;
            return (
              <label key={m.user_id} className={isSelfOnly ? memberRowDisabledClass : memberRowClass}>
                <input
                  type="checkbox"
                  className={checkboxClass}
                  checked={checked}
                  disabled={isSelfOnly}
                  onChange={() => {
                    if (isSelfOnly) return;
                    setSelectedForRevoke((prev) => {
                      const next = new Set(prev);
                      if (next.has(m.user_id)) next.delete(m.user_id);
                      else next.add(m.user_id);
                      return next;
                    });
                  }}
                />
                <MemberAvatar member={m} />
                <span className={memberNameClass}>{m.display_name || m.username}</span>
                {isSelfOnly && <span className={lockedBadgeClass}>操作不可</span>}
              </label>
            );
          })}
        </div>
        <div className={footerClass}>
          <button type="button" className={btnSecondary} onClick={() => setScreen("list")}>
            戻る
          </button>
          <button
            type="button"
            className={btnDanger}
            onClick={confirmRevoke}
            disabled={selectedForRevoke.size === 0}
          >
            削除 ({selectedForRevoke.size}名)
          </button>
        </div>
      </ModalFrame>
    );
  }

  // ── Screen: メンバー一覧（デフォルト） ──
  const displayName = (m: Member) => m.display_name || m.username;
  return (
    <ModalFrame onBackdropClick={onClose}>
      <div className={headerClass}>
        <div>
          <p className={modalTitle}>{roleName}</p>
          <p className={modalSubtitle}>このロールを持つメンバー ({currentMembers.length}名)</p>
        </div>
      </div>

      <div className={memberListClass}>
        {currentMembers.length === 0 && (
          <p className={emptyClass}>メンバーがいません</p>
        )}
        {currentMembers.map((m) => (
          <div key={m.user_id} className={memberRowBaseClass}>
            <MemberAvatar member={m} />
            <span className={memberNameClass}>{displayName(m)}</span>
            <span className="shrink-0 text-xs text-slate-500">@{m.username}</span>
          </div>
        ))}
      </div>

      <div className={footerClass}>
        {!readOnly && !isLocked && (
          <div className="flex gap-2">
            <button
              type="button"
              className={btnDanger}
              onClick={() => { setSearch(""); setSelectedForRevoke(new Set()); setScreen("revoke"); }}
              disabled={localMemberIds.size === 0}
            >
              削除
            </button>
            <button
              type="button"
              className={btnPrimary}
              onClick={() => { setSearch(""); setSelectedForGrant(new Set()); setScreen("grant"); }}
            >
              付与
            </button>
          </div>
        )}
        {isLocked && (
          <span className={lockedMsgClass}><span aria-hidden="true">🔒</span>Botより上位のロールは編集できません</span>
        )}
        {readOnly && (
          <span className={lockedMsgClass}><span aria-hidden="true">🔒</span>閲覧のみ（付与・削除は各カテゴリから行えます）</span>
        )}
        <div className="flex gap-2">
          <button type="button" className={btnSecondary} onClick={onClose}>
            戻る
          </button>
          {!readOnly && (
            <button
              type="button"
              className={btnPrimary}
              onClick={handleCommit}
              disabled={!hasChanges}
            >
              変更を確定
            </button>
          )}
        </div>
      </div>
    </ModalFrame>
  );
}
