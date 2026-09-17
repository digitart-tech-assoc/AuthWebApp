"use client";

import styles from "./roles.module.css";
import type { RoleDiffData } from "@/types/roles";

interface Props {
  diffData: RoleDiffData;
  onClose: () => void;
  onConfirm: () => void;
}

export default function RoleDiffModal({ diffData, onClose, onConfirm }: Props) {
  const hasChanges =
    diffData.roleAdded.length > 0 ||
    diffData.memberAssigned.length > 0 ||
    diffData.permissionEdited.length > 0 ||
    diffData.orderChanged.length > 0 ||
    diffData.roleDeleted.length > 0 ||
    diffData.categoriesAdded.length > 0 ||
    diffData.categoriesDeleted.length > 0;

  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div className={styles.modal} role="dialog" aria-label="変更内容確認">
        <div className={styles.header}>
          <p className={styles.title}>変更内容の確認</p>
          <p className={styles.subtitle}>以下の変更をDBに保存し、Discordへ同期します</p>
        </div>
        <div style={{ maxHeight: "400px", overflowY: "auto", padding: "20px", fontSize: "14px", borderBottom: "1px solid #e5e7eb" }}>
          {hasChanges ? (
            <>
              {diffData.roleAdded.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#10b981", marginBottom: "8px" }}>
                    ＋ ロールを追加（{diffData.roleAdded.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.roleAdded.map((item) => (
                      <li key={item.role.role_id}>
                        <strong>{item.role.name}</strong>
                        {item.memberCount > 0 && (
                          <div style={{ marginLeft: "12px", color: "#6b7280", fontSize: "12px" }}>
                            👥 {item.memberCount}名割り当て
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {diffData.memberAssigned.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#8b5cf6", marginBottom: "8px" }}>
                    👥 メンバーを割り当て（{diffData.memberAssigned.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.memberAssigned.map((change) => (
                      <li key={change.roleId}>
                        <strong>{change.roleName}</strong>
                        {change.added.length > 0 && (
                          <div style={{ marginLeft: "12px", color: "#10b981" }}>➕ {change.added.length}名追加</div>
                        )}
                        {change.removed.length > 0 && (
                          <div style={{ marginLeft: "12px", color: "#ef4444" }}>➖ {change.removed.length}名削除</div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {diffData.permissionEdited.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#f59e0b", marginBottom: "8px" }}>
                    🔒 権限を編集（{diffData.permissionEdited.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.permissionEdited.map((item) => (
                      <li key={item.roleId}>
                        <strong>{item.roleName}</strong>
                        <div style={{ marginLeft: "12px", color: "#6b7280", fontSize: "12px" }}>
                          {item.oldPermissions} → {item.newPermissions}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {diffData.orderChanged.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#3b82f6", marginBottom: "8px" }}>
                    📍 表示する順番を変更（{diffData.orderChanged.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.orderChanged.map((item) => (
                      <li key={item.roleId}>
                        <strong>{item.roleName}</strong>
                        <div style={{ marginLeft: "12px", color: "#6b7280", fontSize: "12px" }}>
                          位置: {item.oldPosition} → {item.newPosition}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {diffData.roleDeleted.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#ef4444", marginBottom: "8px" }}>
                    ✕ ロール削除（{diffData.roleDeleted.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.roleDeleted.map((r) => (
                      <li key={r.role_id}>{r.name}</li>
                    ))}
                  </ul>
                </div>
              )}

              {diffData.categoriesAdded.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#10b981", marginBottom: "8px" }}>
                    ＋ カテゴリ追加（{diffData.categoriesAdded.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.categoriesAdded.map((c) => (
                      <li key={c.id}>{c.name}</li>
                    ))}
                  </ul>
                </div>
              )}

              {diffData.categoriesDeleted.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontWeight: "bold", color: "#ef4444", marginBottom: "8px" }}>
                    ✕ カテゴリ削除（{diffData.categoriesDeleted.length}件）
                  </div>
                  <ul style={{ margin: "0 0 0 20px", paddingLeft: "0" }}>
                    {diffData.categoriesDeleted.map((c) => (
                      <li key={c.id}>{c.name}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p style={{ color: "#6b7280" }}>変更がありません</p>
          )}
        </div>
        <div className={styles.footer}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>
            キャンセル
          </button>
          <button type="button" className={styles.confirmBtn} onClick={onConfirm}>
            保存してDiscordへ送信
          </button>
        </div>
      </div>
    </>
  );
}
