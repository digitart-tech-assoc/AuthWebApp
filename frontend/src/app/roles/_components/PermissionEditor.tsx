// 役割: Discord権限エディターパネル（スライドアウト）

"use client";

import { useState, useEffect, useCallback } from "react";
import ToggleSwitch from "./ToggleSwitch";
import { btnPrimary, btnSecondary, modalFooter } from "./roleStyles";

// ===== Discord permission definitions =====

export const DISCORD_PERMISSIONS = [
  {
    category: "一般",
    perms: [
      { bit: 3n,  name: "管理者",           description: "すべての権限を持ち、上書き不可" },
      { bit: 5n,  name: "サーバー管理",     description: "サーバー名・アイコンなどを変更" },
      { bit: 28n, name: "ロール管理",        description: "自分より低いロールを管理" },
      { bit: 4n,  name: "チャンネル管理",   description: "チャンネルの作成・編集・削除" },
      { bit: 29n, name: "Webhook管理",       description: "Webhookの作成・編集・削除" },
      { bit: 7n,  name: "監査ログ閲覧",     description: "サーバーの変更履歴を確認" },
    ],
  },
  {
    category: "メンバー",
    perms: [
      { bit: 0n,  name: "招待リンク作成",   description: "サーバーへの招待リンクを作成" },
      { bit: 1n,  name: "メンバーをキック", description: "サーバーからメンバーを追放" },
      { bit: 2n,  name: "メンバーをBAN",    description: "メンバーを永久追放" },
      { bit: 40n, name: "タイムアウト",     description: "メンバーを一時的にミュート" },
      { bit: 26n, name: "ニックネーム変更", description: "自分のニックネームを変更" },
      { bit: 27n, name: "ニックネーム管理", description: "他メンバーのニックネームを変更" },
    ],
  },
  {
    category: "テキストチャンネル",
    perms: [
      { bit: 10n, name: "チャンネル閲覧",   description: "テキスト・ボイスチャンネルを見る" },
      { bit: 11n, name: "メッセージ送信",   description: "テキストチャンネルへメッセージを送る" },
      { bit: 14n, name: "URLリンク埋め込み",description: "送信したURLをプレビュー表示" },
      { bit: 15n, name: "ファイル添付",     description: "ファイル・画像を送信" },
      { bit: 16n, name: "メッセージ履歴閲覧",description: "過去のメッセージを読む" },
      { bit: 6n,  name: "リアクション追加", description: "メッセージにリアクションを付ける" },
      { bit: 13n, name: "メッセージ管理",   description: "他人のメッセージを削除・ピン留め" },
      { bit: 17n, name: "@everyone @here メンション", description: "全員へのメンションを許可" },
      { bit: 18n, name: "外部絵文字使用",   description: "他サーバーの絵文字を使用" },
      { bit: 31n, name: "スラッシュコマンド", description: "ボットのスラッシュコマンドを使用" },
      { bit: 35n, name: "スレッド作成",     description: "公開スレッドを作成" },
    ],
  },
  {
    category: "ボイスチャンネル",
    perms: [
      { bit: 20n, name: "接続",             description: "ボイスチャンネルに参加" },
      { bit: 21n, name: "発言",             description: "ボイスチャンネルで話す" },
      { bit: 9n,  name: "動画送信",         description: "カメラ映像・画面共有" },
      { bit: 22n, name: "メンバーをミュート", description: "他メンバーのマイクをミュート" },
      { bit: 23n, name: "メンバーのスピーカー解除",description: "他メンバーのスピーカーを解除" },
      { bit: 24n, name: "メンバーを移動",   description: "他メンバーをチャンネル間で移動" },
    ],
  },
] as const;

import type { PermissionTarget } from "@/types/roles";
export type { PermissionTarget };

type Props = {
  target: PermissionTarget;
  botPermissions: bigint;
  onSave: (newPermissions: number) => void;
  onClose: () => void;
};

// ===== Utility =====

function hasBitExact(perms: bigint, bit: bigint): boolean {
  return Boolean((perms >> bit) & 1n);
}

function setBit(perms: bigint, bit: bigint, value: boolean): bigint {
  if (value) return perms | (1n << bit);
  return perms & ~(1n << bit);
}

// ===== Main Component =====

export default function PermissionEditorPanel({ target, botPermissions, onSave, onClose }: Props) {
  const [perms, setPerms] = useState<bigint>(BigInt(target.currentPermissions));
  const catPerms = BigInt(target.categoryPermissions ?? 0);
  const isAdminActive = hasBitExact(perms, 3n);
  const botHasAdmin = hasBitExact(botPermissions, 3n);

  useEffect(() => {
    setPerms(BigInt(target.currentPermissions));
  }, [target]);

  const toggleBit = useCallback((bit: bigint) => {
    setPerms((prev) => {
      const current = hasBitExact(prev, bit);
      return setBit(prev, bit, !current);
    });
  }, []);

  function applyCategory() {
    setPerms(BigInt(target.categoryPermissions ?? 0));
  }

  function handleSave() {
    onSave(Number(perms));
  }

  const hasChanges = perms !== BigInt(target.currentPermissions);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/40 animate-fade-in" onClick={onClose} />

      {/* Panel */}
      <div
        className="relative flex h-full w-full max-w-lg flex-col bg-white shadow-xl animate-slide-in-right"
        role="dialog"
        aria-modal="true"
        aria-label="権限設定"
      >
        {/* Header */}
        <div className="flex items-start gap-2.5 border-b border-slate-200 px-5 pt-5 pb-4">
          <div className="min-w-0 flex-1">
            <p className="m-0 truncate text-base font-bold text-slate-900">
              {target.name}
            </p>
            {target.kind === "role" && target.categoryPermissions !== undefined && (
              <span className="mt-1 inline-flex items-center gap-1 whitespace-nowrap rounded-md bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                カテゴリ権限を参照中
              </span>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 overflow-y-auto">
          {/* Category inherit banner (for roles only) */}
          {target.kind === "role" && target.categoryPermissions !== undefined && target.categoryPermissions !== 0 && (
            <div className="mx-5 my-3 flex flex-wrap items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
              <span>カテゴリの権限設定を一括適用できます</span>
              <button
                type="button"
                className="ml-auto inline-flex h-8 items-center whitespace-nowrap rounded-md bg-blue-600 px-2.5 text-xs font-semibold text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                onClick={applyCategory}
              >
                カテゴリ権限を適用
              </button>
            </div>
          )}

          {/* Administrator warning */}
          {isAdminActive && (
            <div className="mx-5 mb-2.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              ⚠️ 「管理者」が有効なため、他の権限はすべて自動的に有効になります。
            </div>
          )}

          {/* Permission sections */}
          {DISCORD_PERMISSIONS.map((section) => (
            <div key={section.category} className="pb-2">
              <div className="px-5 pt-3.5 pb-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                {section.category}
              </div>
              {section.perms.map((perm) => {
                const isEnabled = hasBitExact(perms, perm.bit);
                const isFromAdmin = isAdminActive && perm.bit !== 3n;

                // --- BOT PERMISSION CHECK ---
                const isBotAllowed = botHasAdmin || hasBitExact(botPermissions, perm.bit);

                const isInheritedFromCat =
                  target.kind === "role" &&
                  target.categoryPermissions !== undefined &&
                  hasBitExact(catPerms, perm.bit) === isEnabled;

                return (
                  <div
                    key={String(perm.bit)}
                    className={`flex items-center gap-3 border-t border-slate-100 px-5 py-2.5 transition-colors hover:bg-slate-50 ${isFromAdmin || !isBotAllowed ? "opacity-50" : ""}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-slate-900">
                        {perm.name}
                        {!isBotAllowed && <span className="ml-1.5 align-middle text-xs font-semibold text-red-600">(Bot権限不足)</span>}
                      </div>
                      <div className="mt-0.5 text-xs text-slate-500">{perm.description}</div>
                    </div>
                    {isInheritedFromCat && !isFromAdmin && (
                      <span className="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-xs font-semibold text-blue-700">
                        カテゴリと同じ
                      </span>
                    )}
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

        {/* Footer */}
        <div className={modalFooter}>
          <button type="button" className={btnSecondary} onClick={onClose}>
            戻る
          </button>
          <button
            type="button"
            className={btnPrimary}
            onClick={handleSave}
            disabled={!hasChanges}
          >
            適用
          </button>
        </div>
      </div>
    </div>
  );
}
