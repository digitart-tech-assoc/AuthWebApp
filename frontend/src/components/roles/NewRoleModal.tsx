// 役割: 新規ロール作成モーダル

"use client";

import { useState, useEffect } from "react";
import { DISCORD_PERMISSIONS } from "./PermissionEditor";
import styles from "./newrole.module.css";

type Category = {
  id: string;
  name: string;
  permissions: number;
};

type NewRoleData = {
  role_id: string;
  name: string;
  color: string;
  hoist: boolean;
  mentionable: boolean;
  permissions: number;
  position: number;
  category_id: string | null;
  is_our_bot?: boolean;
};

type Props = {
  categories: Category[];
  botPermissions: bigint;
  onCreated: (role: NewRoleData) => void;
  onClose: () => void;
  isMember?: boolean;
  restrictedCategoryNames?: Set<string>;
};

// ===== Preset palette (Discord-like) =====
const PALETTE = [
  "#99AAB5", "#1ABC9C", "#2ECC71", "#3498DB", "#9B59B6",
  "#E91E63", "#F1C40F", "#E67E22", "#E74C3C", "#95A5A6",
  "#607D8B", "#11806A", "#1F8B4C", "#206694", "#71368A",
  "#AD1457", "#C27C0E", "#A84300", "#992D22", "#000000",
];

function hasBitExact(perms: bigint, bit: bigint): boolean {
  return Boolean((perms >> bit) & 1n);
}
function setBit(perms: bigint, bit: bigint, value: boolean): bigint {
  return value ? perms | (1n << bit) : perms & ~(1n << bit);
}

export default function NewRoleModal({ categories, botPermissions, onCreated, onClose, isMember = false, restrictedCategoryNames = new Set() }: Props) {
  const [name, setName] = useState("");
  const [color, setColor] = useState("#99AAB5");
  const [hexInput, setHexInput] = useState("#99AAB5");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [perms, setPerms] = useState<bigint>(0n);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"basic" | "permissions">("basic");

  // 固定値: Hoist=false, Mentionable=true
  const hoist = false;
  const mentionable = true;

  // When category changes, inherit its permissions (but member can't set permissions except for 会員情報)
  useEffect(() => {
    const cat = categories.find((c) => c.id === categoryId);
    const canSetPermissions = !isMember || cat?.name === "会員情報";
    if (canSetPermissions) {
      setPerms(BigInt(cat?.permissions ?? 0));
    } else {
      // member: 会員情報以外は権限を常に 0 に固定
      setPerms(0n);
    }
  }, [categoryId, categories, isMember]);

  // memberモード: 最初の利用可能なカテゴリを自動選択
  useEffect(() => {
    if (isMember && categoryId === null) {
      const first = categories.find((c) => !restrictedCategoryNames.has(c.name));
      if (first) setCategoryId(first.id);
    }
  }, [isMember, categories, restrictedCategoryNames, categoryId]);

  function handleColorPick(c: string) {
    setColor(c);
    setHexInput(c);
  }

  function handleHexChange(v: string) {
    setHexInput(v);
    if (/^#[0-9a-fA-F]{6}$/.test(v)) setColor(v);
  }

  function toggleBit(bit: bigint) {
    setPerms((prev) => {
      const curr = hasBitExact(prev, bit);
      return setBit(prev, bit, !curr);
    });
  }

  const isAdminActive = hasBitExact(perms, 3n);
  const botHasAdmin = hasBitExact(botPermissions, 3n);
  
  // member が権限を設定できるかどうか判定
  const selectedCategory = categories.find((c) => c.id === categoryId);
  const canSetPermissions = !isMember || selectedCategory?.name === "会員情報";

  async function handleCreate() {
    if (!name.trim()) {
      setError("ロール名を入力してください");
      return;
    }
    // memberモード: カテゴリ必須チェック
    if (isMember && !categoryId) {
      setError("ロールを作成するカテゴリを選択してください");
      return;
    }
    setError(null);

    const draftId = `draft-${Date.now()}`;
    onCreated({
      role_id: draftId,
      name: name.trim(),
      color,
      hoist,
      mentionable,
      permissions: Number(perms),
      category_id: categoryId,
      position: 0, // position will be sorted out locally
    });
  }

  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div className={styles.modal} role="dialog" aria-label="新規ロール作成">
        {/* Header */}
        <div className={styles.header}>
          <div>
            <p className={styles.title}>＋ 新規ロールを作成</p>
            <p className={styles.subtitle}>データベースに下書きとして保存します（Discordへの反映は「送信」を押してください）</p>
          </div>
        </div>

        {/* Tabs */}
        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${step === "basic" ? styles.activeTab : ""}`}
            onClick={() => setStep("basic")}
          >
            基本設定
          </button>
          {canSetPermissions && (
            <button
              type="button"
              className={`${styles.tab} ${step === "permissions" ? styles.activeTab : ""}`}
              onClick={() => setStep("permissions")}
            >
              権限設定
            </button>
          )}
        </div>

        {/* Body */}
        <div className={styles.body}>
          {step === "basic" && (
            <div className={styles.basicSection}>
              {/* Preview */}
              <div className={styles.preview}>
                <span
                  className={styles.previewDot}
                  style={{ backgroundColor: color === "#000000" ? "#d1d5db" : color }}
                />
                <span className={styles.previewName}>{name || "（ロール名）"}</span>
              </div>

              {/* Name */}
              <label className={styles.fieldLabel}>ロール名 <span className={styles.required}>*</span></label>
              <input
                type="text"
                className={styles.textInput}
                placeholder="例: メンバー、モデレーター"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />

              {/* Category */}
              <label className={styles.fieldLabel}>カテゴリ{isMember && <span className={styles.required}> *</span>}</label>
              {isMember && (
                <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
                  禁止カテゴリ（会員情報・学部学科・学年）およびカテゴリに属さない状態での作成できません
                </p>
              )}
              <select
                className={styles.select}
                value={categoryId ?? ""}
                onChange={(e) => setCategoryId(e.target.value || null)}
              >
                {!isMember && <option value="">カテゴリなし</option>}
                {categories
                  .filter((c) => !restrictedCategoryNames.has(c.name))
                  .map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
              </select>

              {/* Color palette */}
              <label className={styles.fieldLabel}>カラー</label>
              <div className={styles.palette}>
                {PALETTE.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`${styles.paletteColor} ${color === c ? styles.selectedColor : ""}`}
                    style={{ backgroundColor: c }}
                    onClick={() => handleColorPick(c)}
                    title={c}
                  />
                ))}
              </div>
              <div className={styles.hexRow}>
                <div
                  className={styles.hexSwatch}
                  style={{ backgroundColor: color }}
                />
                <input
                  type="text"
                  className={styles.hexInput}
                  value={hexInput}
                  onChange={(e) => handleHexChange(e.target.value)}
                  placeholder="#99AAB5"
                  maxLength={7}
                />
              </div>

              {/* Toggles */}
              <div className={styles.toggleRow}>
                <div>
                  <div className={styles.toggleLabel}>メンバーをオンライン一覧で分けて表示</div>
                  <div className={styles.toggleDesc}>（Hoist）- 固定: オフ</div>
                </div>
                <label className={styles.switch}>
                  <input type="checkbox" checked={hoist} disabled />
                  <span className={styles.switchSlider} />
                </label>
              </div>
              <div className={styles.toggleRow}>
                <div>
                  <div className={styles.toggleLabel}>このロールを誰でもメンションできるようにする</div>
                  <div className={styles.toggleDesc}>（Mentionable）- 固定: オン</div>
                </div>
                <label className={styles.switch}>
                  <input type="checkbox" checked={mentionable} disabled />
                  <span className={styles.switchSlider} />
                </label>
              </div>
            </div>
          )}

          {step === "permissions" && (
            <div className={styles.permSection}>
              {categoryId && (
                <div className={styles.inheritNote}>
                  📋 選択したカテゴリの権限を初期値として引き継いでいます
                </div>
              )}
              {isAdminActive && (
                <div className={styles.adminWarn}>
                  ⚠️ 「管理者」が有効なため、他の権限はすべて自動的に有効になります
                </div>
              )}
              {DISCORD_PERMISSIONS.map((section) => (
                <div key={section.category} className={styles.permSection2}>
                  <div className={styles.permSectionLabel}>{section.category}</div>
                  {section.perms.map((perm) => {
                    const isEnabled = hasBitExact(perms, perm.bit);
                    const isFromAdmin = isAdminActive && perm.bit !== 3n;
                    const isBotAllowed = botHasAdmin || hasBitExact(botPermissions, perm.bit);

                    return (
                      <div
                        key={String(perm.bit)}
                        className={`${styles.permRow} ${isFromAdmin ? styles.dimmed : ""} ${!isBotAllowed ? styles.disabledRow : ""}`}
                      >
                        <div className={styles.permInfo}>
                          <div className={styles.permName}>
                            {perm.name}
                            {!isBotAllowed && <span className={styles.botLacksMsg}>(Bot権限不足)</span>}
                          </div>
                          <div className={styles.permDesc}>{perm.description}</div>
                        </div>
                        <label className={styles.switch}>
                          <input
                            type="checkbox"
                            checked={isFromAdmin ? true : isEnabled}
                            disabled={isFromAdmin || !isBotAllowed}
                            onChange={() => !isFromAdmin && isBotAllowed && toggleBit(perm.bit)}
                          />
                          <span className={styles.switchSlider} />
                        </label>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          {error && <span className={styles.errorMsg}>✕ {error}</span>}
          <button type="button" className={styles.cancelBtn} onClick={onClose}>戻る</button>
          <button
            type="button"
            className={styles.createBtn}
            onClick={handleCreate}
            disabled={!name.trim()}
          >
            作成
          </button>
        </div>
      </div>
    </>
  );
}
