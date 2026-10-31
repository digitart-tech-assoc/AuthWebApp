// 役割: ロール作成・編集モーダル

"use client";

import { useState, useEffect } from "react";
import { displayMessage } from "@/lib/errorMessages";
import { DISCORD_PERMISSIONS } from "./PermissionEditor";
import ModalFrame from "./ModalFrame";
import ToggleSwitch from "./ToggleSwitch";
import {
  btnPrimary, btnSecondary, fieldLabel, modalBody, modalErrorMsg, modalFooter, modalHeader,
  modalSubtitle, modalTitle, requiredMark, selectInput, textInput, toggleDesc, toggleLabel, toggleRow,
} from "./roleStyles";

type Category = {
  id: string;
  name: string;
  permissions: number;
};

type RoleData = {
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
  /** Promise を返すと完了まで「作成」を押せなくする。DisplayableError を送出するとその文言を表示する */
  onSaved: (role: RoleData) => void | Promise<void>;
  onClose: () => void;
  /** カテゴリの選択肢から除くカテゴリ（管理者専用カテゴリ） */
  restrictedCategoryIds?: Set<string>;
  /** 編集モード: 既存ロールを渡すと編集UIになる */
  editingRole?: RoleData | null;
  /** member のロール作成: 作成先のカテゴリを固定し、権限設定を出さない（permissions は 0 固定） */
  memberCategoryId?: string;
};

// ===== Preset palette (Discord-like) =====
const PALETTE = [
  "#99AAB5", "#1ABC9C", "#2ECC71", "#3498DB", "#9B59B6",
  "#E91E63", "#F1C40F", "#E67E22", "#E74C3C", "#95A5A6",
  "#607D8B", "#11806A", "#1F8B4C", "#206694", "#71368A",
  "#AD1457", "#C27C0E", "#A84300", "#992D22", "#000000",
];

const tabBase =
  "-mb-px h-10 rounded-t-md border-b-2 px-3.5 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
const tabClass = (active: boolean) =>
  `${tabBase} ${active ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-900"}`;

function hasBitExact(perms: bigint, bit: bigint): boolean {
  return Boolean((perms >> bit) & 1n);
}
function setBit(perms: bigint, bit: bigint, value: boolean): bigint {
  return value ? perms | (1n << bit) : perms & ~(1n << bit);
}

export default function NewRoleModal({
  categories, botPermissions, onSaved, onClose,
  restrictedCategoryIds = new Set(),
  editingRole = null,
  memberCategoryId,
}: Props) {
  const isEditMode = !!editingRole;
  const isMemberMode = memberCategoryId !== undefined;

  const [name, setName] = useState(editingRole?.name ?? "");
  const [color, setColor] = useState(editingRole?.color ?? "#99AAB5");
  const [hexInput, setHexInput] = useState(editingRole?.color ?? "#99AAB5");
  const [categoryId, setCategoryId] = useState<string | null>(editingRole?.category_id ?? memberCategoryId ?? null);
  const [perms, setPerms] = useState<bigint>(BigInt(editingRole?.permissions ?? 0));
  // 新規作成時の初期値はオン。member が作成するロールはトグルを無効にしてオンで固定（Backend の self-create も固定している）
  const [mentionable, setMentionable] = useState(editingRole?.mentionable ?? true);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"basic" | "permissions">("basic");
  const [saving, setSaving] = useState(false);

  // 固定値: Hoist=false
  const hoist = false;

  // When category changes (新規作成時のみ), inherit its permissions
  useEffect(() => {
    if (isEditMode) return; // 編集モードではカテゴリ変更で権限は上書きしない
    if (isMemberMode) return; // member が作成するロールは権限なし（0）で固定
    const cat = categories.find((c) => c.id === categoryId);
    setPerms(BigInt(cat?.permissions ?? 0));
  }, [categoryId, categories, isEditMode, isMemberMode]);

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

  async function handleSave() {
    if (!name.trim()) {
      setError("ロール名を入力してください");
      return;
    }
    setError(null);

    const roleId = isEditMode ? editingRole!.role_id : `draft-${Date.now()}`;
    setSaving(true);
    try {
      await onSaved({
        role_id: roleId,
        name: name.trim(),
        color,
        hoist,
        mentionable,
        permissions: isMemberMode ? 0 : Number(perms),
        category_id: categoryId,
        position: editingRole?.position ?? 0,
        is_our_bot: editingRole?.is_our_bot,
      });
    } catch (e) {
      setError(displayMessage(e, "保存に失敗しました。接続を確認してください。"));
    } finally {
      setSaving(false);
    }
  }

  const memberCategoryName = categories.find((c) => c.id === memberCategoryId)?.name;

  return (
    <ModalFrame onBackdropClick={onClose} size="xl" ariaLabel={isEditMode ? "ロール編集" : "新規ロール作成"}>
      {/* Header */}
      <div className={modalHeader}>
        <div>
          <p className={modalTitle}>{isEditMode ? "✏ ロールを編集" : "＋ 新規ロールを作成"}</p>
          <p className={modalSubtitle}>
            {isMemberMode
              ? "作成するとDiscordにロールが作られ、あなたに付与されます。ロールはサーバー全体で共有され、他のメンバーも付与できます（編集・削除は管理者のみ）"
              : isEditMode
                ? "変更を確定すると、DBへの保存とDiscordへの同期が自動で行われます"
                : "作成を確定すると、DBへの保存とDiscordへの同期が自動で行われます"}
          </p>
        </div>
      </div>

      {/* Tabs（member の作成では権限を設定しないため出さない） */}
      <div className={`${isMemberMode ? "hidden" : "flex"} shrink-0 gap-0.5 border-b border-slate-200 px-6 pt-3`}>
        <button
          type="button"
          className={tabClass(step === "basic")}
          onClick={() => setStep("basic")}
        >
          基本設定
        </button>
        <button
          type="button"
          className={tabClass(step === "permissions")}
          onClick={() => setStep("permissions")}
        >
          権限設定
        </button>
      </div>

      {/* Body */}
      <div className={modalBody}>
        {step === "basic" && (
          <div className="flex flex-col gap-3">
            {/* Preview */}
            <div className="flex items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5">
              <span
                className="size-3.5 shrink-0 rounded-full"
                style={{ backgroundColor: color === "#000000" ? "#d1d5db" : color }}
              />
              <span className="text-sm font-semibold text-slate-900">{name || "（ロール名）"}</span>
            </div>

            {/* Name */}
            <label className={fieldLabel}>ロール名 <span className={requiredMark}>*</span></label>
            <input
              type="text"
              className={textInput}
              placeholder={isMemberMode ? "例: Minecraft、Python" : "例: メンバー、モデレーター"}
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={isMemberMode ? 100 : undefined}
              autoFocus
            />

            {/* Category */}
            <label className={fieldLabel}>カテゴリ</label>
            {isMemberMode ? (
              <div className="text-sm font-semibold text-slate-900">{memberCategoryName}</div>
            ) : (
              <select
                className={selectInput}
                value={categoryId ?? ""}
                onChange={(e) => setCategoryId(e.target.value || null)}
              >
                <option value="">カテゴリなし</option>
                {categories
                  .filter((c) => !restrictedCategoryIds.has(c.id))
                  .map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
              </select>
            )}

            {/* Color palette */}
            <label className={fieldLabel}>カラー</label>
            <div className="flex flex-wrap gap-2">
              {PALETTE.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`size-8 cursor-pointer rounded-full p-0 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${color === c ? "scale-110 ring-2 ring-blue-600 ring-offset-2" : ""}`}
                  style={{ backgroundColor: c }}
                  onClick={() => handleColorPick(c)}
                  title={c}
                  aria-label={`カラー ${c}`}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <div
                className="size-10 shrink-0 rounded-lg border border-slate-300"
                style={{ backgroundColor: color }}
              />
              <input
                type="text"
                className="h-10 w-32 rounded-lg border border-slate-300 bg-slate-50 px-3 font-mono text-sm text-slate-900 transition-colors focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20"
                value={hexInput}
                onChange={(e) => handleHexChange(e.target.value)}
                placeholder="#99AAB5"
                maxLength={7}
                aria-label="カラーコード"
              />
            </div>

            {/* Toggles */}
            <div className={toggleRow}>
              <div>
                <div className={toggleLabel}>メンバーをオンライン一覧で分けて表示</div>
                <div className={toggleDesc}>（Hoist）- 固定: オフ</div>
              </div>
              <ToggleSwitch checked={hoist} disabled ariaLabel="Hoist" />
            </div>
            <div className={toggleRow}>
              <div>
                <div className={toggleLabel}>このロールを誰でもメンションできるようにする</div>
                <div className={toggleDesc}>（Mentionable）{isMemberMode && "- 固定: オン"}</div>
              </div>
              <ToggleSwitch
                checked={mentionable}
                disabled={isMemberMode}
                onChange={setMentionable}
                ariaLabel="Mentionable"
              />
            </div>
          </div>
        )}

        {step === "permissions" && !isMemberMode && (
          <div className="flex flex-col">
            {categoryId && (
              <div className="mb-2.5 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
                📋 選択したカテゴリの権限を初期値として引き継いでいます
              </div>
            )}
            {isAdminActive && (
              <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                ⚠️ 「管理者」が有効なため、他の権限はすべて自動的に有効になります
              </div>
            )}
            {DISCORD_PERMISSIONS.map((section) => (
              <div key={section.category} className="mb-1">
                <div className="pt-2.5 pb-1 text-xs font-bold uppercase tracking-wider text-slate-500">{section.category}</div>
                {section.perms.map((perm) => {
                  const isEnabled = hasBitExact(perms, perm.bit);
                  const isFromAdmin = isAdminActive && perm.bit !== 3n;
                  const isBotAllowed = botHasAdmin || hasBitExact(botPermissions, perm.bit);

                  return (
                    <div
                      key={String(perm.bit)}
                      className={`flex items-center gap-3 border-t border-slate-100 py-2 transition-opacity ${isFromAdmin || !isBotAllowed ? "opacity-50" : ""}`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-slate-900">
                          {perm.name}
                          {!isBotAllowed && <span className="ml-1.5 align-middle text-xs font-semibold text-red-600">(Bot権限不足)</span>}
                        </div>
                        <div className="mt-0.5 text-xs text-slate-500">{perm.description}</div>
                      </div>
                      <ToggleSwitch
                        checked={isFromAdmin ? true : isEnabled}
                        disabled={isFromAdmin || !isBotAllowed}
                        onChange={() => !isFromAdmin && isBotAllowed && toggleBit(perm.bit)}
                        ariaLabel={perm.name}
                      />
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={modalFooter}>
        {error && <span className={modalErrorMsg}>✕ {error}</span>}
        <button type="button" className={btnSecondary} onClick={onClose} disabled={saving}>戻る</button>
        <button
          type="button"
          className={btnPrimary}
          onClick={handleSave}
          disabled={!name.trim() || saving}
        >
          {isEditMode ? (saving ? "更新中..." : "更新") : (saving ? "作成中..." : "作成")}
        </button>
      </div>
    </ModalFrame>
  );
}
