// 役割: ロールメンバー管理モーダル（付与・削除）

"use client";

import { useState, useMemo } from "react";
import styles from "./rolemember.module.css";

export type Member = {
  user_id: string;
  username: string;
  display_name: string | null;
  avatar: string | null;
};

type Props = {
  roleName: string;
  roleId: string;
  allMembers: Member[];
  /** 現在このロールを持つメンバーのuser_idセット */
  currentMemberIds: string[];
  isLocked?: boolean;
  onCommit: (add: string[], remove: string[]) => void;
  onClose: () => void;
};

type Screen = "list" | "grant" | "revoke";

function MemberAvatar({ member }: { member: Member }) {
  const avatarUrl = member.avatar
    ? `https://cdn.discordapp.com/avatars/${member.user_id}/${member.avatar}.webp?size=32`
    : `https://cdn.discordapp.com/embed/avatars/${Number(member.user_id) % 5}.png`;
  return (
    <img
      src={avatarUrl}
      alt={member.display_name || member.username}
      className={styles.avatar}
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
  onCommit,
  onClose,
}: Props) {
  const [screen, setScreen] = useState<Screen>("list");
  // ローカルの付与済みセット（コミットするまで反映しない）
  const [localMemberIds, setLocalMemberIds] = useState<Set<string>>(
    new Set(currentMemberIds)
  );
  const [selectedForGrant, setSelectedForGrant] = useState<Set<string>>(new Set());
  const [selectedForRevoke, setSelectedForRevoke] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");

  const memberById = useMemo(
    () => new Map(allMembers.map((m) => [m.user_id, m])),
    [allMembers]
  );

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
      <>
        <div className={styles.overlay} onClick={() => setScreen("list")} />
        <div className={styles.modal} role="dialog">
          <div className={styles.header}>
            <span className={styles.title}>ロールを付与するメンバーを選択</span>
            <button type="button" className={styles.closeBtn} onClick={() => setScreen("list")}>✕</button>
          </div>
          <input
            className={styles.search}
            placeholder="名前で検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className={styles.memberList}>
            {filteredAll.map((m) => {
              const alreadyHas = localMemberIds.has(m.user_id);
              const checked = selectedForGrant.has(m.user_id);
              return (
                <label
                  key={m.user_id}
                  className={`${styles.memberRow} ${alreadyHas ? styles.disabled : ""}`}
                >
                  <input
                    type="checkbox"
                    disabled={alreadyHas}
                    checked={checked}
                    onChange={() => {
                      if (alreadyHas) return;
                      setSelectedForGrant((prev) => {
                        const next = new Set(prev);
                        if (next.has(m.user_id)) next.delete(m.user_id);
                        else next.add(m.user_id);
                        return next;
                      });
                    }}
                  />
                  <MemberAvatar member={m} />
                  <span className={styles.memberName}>{m.display_name || m.username}</span>
                  {alreadyHas && <span className={styles.badge}>付与済</span>}
                </label>
              );
            })}
          </div>
          <div className={styles.footer}>
            <button type="button" className={styles.cancelBtn} onClick={() => setScreen("list")}>
              戻る
            </button>
            <button
              type="button"
              className={styles.actionBtn}
              onClick={confirmGrant}
              disabled={selectedForGrant.size === 0}
            >
              決定 ({selectedForGrant.size}名)
            </button>
          </div>
        </div>
      </>
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
      <>
        <div className={styles.overlay} onClick={() => setScreen("list")} />
        <div className={styles.modal} role="dialog">
          <div className={styles.header}>
            <span className={styles.title}>ロールを削除するメンバーを選択</span>
            <button type="button" className={styles.closeBtn} onClick={() => setScreen("list")}>✕</button>
          </div>
          <input
            className={styles.search}
            placeholder="名前で検索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className={styles.memberList}>
            {filteredCurrent.length === 0 && (
              <p className={styles.empty}>このロールを持つメンバーはいません</p>
            )}
            {filteredCurrent.map((m) => {
              const checked = selectedForRevoke.has(m.user_id);
              return (
                <label key={m.user_id} className={styles.memberRow}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      setSelectedForRevoke((prev) => {
                        const next = new Set(prev);
                        if (next.has(m.user_id)) next.delete(m.user_id);
                        else next.add(m.user_id);
                        return next;
                      });
                    }}
                  />
                  <MemberAvatar member={m} />
                  <span className={styles.memberName}>{m.display_name || m.username}</span>
                </label>
              );
            })}
          </div>
          <div className={styles.footer}>
            <button type="button" className={styles.cancelBtn} onClick={() => setScreen("list")}>
              戻る
            </button>
            <button
              type="button"
              className={`${styles.actionBtn} ${styles.revokeBtn}`}
              onClick={confirmRevoke}
              disabled={selectedForRevoke.size === 0}
            >
              削除 ({selectedForRevoke.size}名)
            </button>
          </div>
        </div>
      </>
    );
  }

  // ── Screen: メンバー一覧（デフォルト） ──
  const displayName = (m: Member) => m.display_name || m.username;
  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div className={styles.modal} role="dialog">
        <div className={styles.header}>
          <div>
            <p className={styles.title}>{roleName}</p>
            <p className={styles.subtitle}>このロールを持つメンバー ({currentMembers.length}名)</p>
          </div>
        </div>

        <div className={styles.memberList}>
          {currentMembers.length === 0 && (
            <p className={styles.empty}>メンバーがいません</p>
          )}
          {currentMembers.map((m) => (
            <div key={m.user_id} className={styles.memberRow}>
              <MemberAvatar member={m} />
              <span className={styles.memberName}>{displayName(m)}</span>
              <span className={styles.memberUsername}>@{m.username}</span>
            </div>
          ))}
        </div>

        <div className={styles.footer}>
          {!isLocked && (
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                className={`${styles.actionBtn} ${styles.revokeBtn}`}
                onClick={() => { setSearch(""); setSelectedForRevoke(new Set()); setScreen("revoke"); }}
                disabled={localMemberIds.size === 0}
              >
                削除
              </button>
              <button
                type="button"
                className={styles.actionBtn}
                onClick={() => { setSearch(""); setSelectedForGrant(new Set()); setScreen("grant"); }}
              >
                付与
              </button>
            </div>
          )}
          {isLocked && (
            <span className={styles.lockedMsg}>Botより上位のロールは編集できません</span>
          )}
          <div style={{ display: "flex", gap: "8px" }}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>
              戻る
            </button>
            <button
              type="button"
              className={`${styles.actionBtn} ${!hasChanges ? styles.dimmed : ""}`}
              onClick={handleCommit}
              disabled={!hasChanges}
            >
              変更を確定
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
