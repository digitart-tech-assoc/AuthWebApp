// 役割: Discord権限エディターパネル（スライドアウト）

"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./permission.module.css";

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

// ===== Types =====

export type PermissionTarget = {
  /** "category" | "role" */
  kind: "category" | "role";
  id: string;
  name: string;
  /** For roles: the parent category permissions (for inheritance display) */
  categoryPermissions?: number;
  currentPermissions: number;
  roleDotColor?: string;
};

type Props = {
  target: PermissionTarget;
  onSave: (newPermissions: number) => void;
  onClose: () => void;
};

// ===== Utility =====

function hasBit(perms: bigint, bit: bigint): boolean {
  // Administrator grants everything
  return Boolean((perms >> bit) & 1n) || Boolean((perms >> 3n) & 1n && bit !== 3n);
}

function hasBitExact(perms: bigint, bit: bigint): boolean {
  return Boolean((perms >> bit) & 1n);
}

function setBit(perms: bigint, bit: bigint, value: boolean): bigint {
  if (value) return perms | (1n << bit);
  return perms & ~(1n << bit);
}

// ===== Main Component =====

export default function PermissionEditorPanel({ target, onSave, onClose }: Props) {
  const [perms, setPerms] = useState<bigint>(BigInt(target.currentPermissions));
  const catPerms = BigInt(target.categoryPermissions ?? 0);
  const isAdminActive = hasBitExact(perms, 3n);

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
    <>
      {/* Backdrop */}
      <div className={styles.overlay} onClick={onClose} />

      {/* Panel */}
      <div className={styles.panel} role="dialog" aria-label="権限設定">
        {/* Header */}
        <div className={styles.panelHeader}>
          <div className={styles.panelTitleWrap}>
            <p className={styles.panelTitle}>
              {target.kind === "category" ? "📁 " : "🏷 "}
              {target.name}
            </p>
            <p className={styles.panelSubtitle}>
              {target.kind === "category"
                ? "このカテゴリに含まれるロールのデフォルト権限"
                : "このロール個別の権限設定"}
            </p>
            {target.kind === "role" && target.categoryPermissions !== undefined && (
              <span className={styles.categoryBadge}>カテゴリ権限を参照中</span>
            )}
          </div>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="閉じる">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className={styles.panelBody}>
          {/* Category inherit banner (for roles only) */}
          {target.kind === "role" && target.categoryPermissions !== undefined && target.categoryPermissions !== 0 && (
            <div className={styles.inheritBanner}>
              <span>カテゴリの権限設定を一括適用できます</span>
              <button type="button" className={styles.inheritBannerApply} onClick={applyCategory}>
                カテゴリ権限を適用
              </button>
            </div>
          )}

          {/* Administrator warning */}
          {isAdminActive && (
            <div className={styles.adminWarning}>
              ⚠️ 「管理者」が有効なため、他の権限はすべて自動的に有効になります。
            </div>
          )}

          {/* Permission sections */}
          {DISCORD_PERMISSIONS.map((section) => (
            <div key={section.category} className={styles.section}>
              <div className={styles.sectionLabel}>{section.category}</div>
              {section.perms.map((perm) => {
                const isEnabled = hasBitExact(perms, perm.bit);
                const isFromAdmin = isAdminActive && perm.bit !== 3n;
                const isInheritedFromCat =
                  target.kind === "role" &&
                  target.categoryPermissions !== undefined &&
                  hasBitExact(catPerms, perm.bit) === isEnabled;

                return (
                  <div
                    key={String(perm.bit)}
                    className={`${styles.permRow} ${isFromAdmin ? styles.inherited : ""}`}
                  >
                    <div className={styles.permInfo}>
                      <div className={styles.permName}>{perm.name}</div>
                      <div className={styles.permDesc}>{perm.description}</div>
                    </div>
                    {isInheritedFromCat && !isFromAdmin && (
                      <span className={styles.inheritedTag}>カテゴリと同じ</span>
                    )}
                    <label className={styles.toggle}>
                      <input
                        type="checkbox"
                        checked={isFromAdmin ? true : isEnabled}
                        disabled={isFromAdmin}
                        onChange={() => !isFromAdmin && toggleBit(perm.bit)}
                        aria-label={perm.name}
                      />
                      <span className={styles.toggleSlider} />
                    </label>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className={styles.panelFooter}>
          <span className={styles.footerHint}>
            変更は「保存する」フロートバーで確定されます
          </span>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>
            キャンセル
          </button>
          <button
            type="button"
            className={styles.saveBtn}
            onClick={handleSave}
            disabled={!hasChanges}
          >
            適用
          </button>
        </div>
      </div>
    </>
  );
}
