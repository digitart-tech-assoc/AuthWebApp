// 役割: カテゴリ編集モーダル

"use client";

import { useState } from "react";
import styles from "./newrole.module.css"; // Reuse new role modal styles

type Category = {
  id: string;
  name: string;
  display_order: number;
  is_collapsed: boolean;
  permissions: number;
  is_restricted: boolean;
};

type Props = {
  category: Category;
  isAdmin: boolean;
  onSaved: (categoryId: string, name: string, is_restricted: boolean) => void;
  onClose: () => void;
};

export default function EditCategoryModal({ category, isAdmin, onSaved, onClose }: Props) {
  const [name, setName] = useState(category.name);
  const [isRestricted, setIsRestricted] = useState(category.is_restricted);

  function handleSave() {
    const trimmed = name.trim();
    if (!trimmed) return;
    onSaved(category.id, trimmed, isRestricted);
  }

  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div className={styles.modal}>
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>カテゴリの編集</h2>
            <p className={styles.subtitle}>カテゴリ名や管理者専用設定を変更します</p>
          </div>
          <button type="button" className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div className={styles.body}>
          <div className={styles.basicSection}>
            <label className={styles.fieldLabel}>カテゴリ名 <span className={styles.required}>*</span></label>
            <input
              type="text"
              className={styles.textInput}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="カテゴリ名"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter" && name.trim()) handleSave();
              }}
            />

            {isAdmin && (
              <div className={styles.toggleRow}>
                <div>
                  <div className={styles.toggleLabel}>管理者専用カテゴリ</div>
                  <div className={styles.toggleDesc}>
                    オンにすると、メンバーは自分がこのカテゴリ内のロールを付与・解除できなくなります。
                  </div>
                </div>
                <label className={styles.switch}>
                  <input
                    type="checkbox"
                    checked={isRestricted}
                    onChange={(e) => setIsRestricted(e.target.checked)}
                  />
                  <span className={styles.switchSlider} />
                </label>
              </div>
            )}
          </div>
        </div>

        <div className={styles.footer}>
          {!name.trim() && <div className={styles.errorMsg}>カテゴリ名を入力してください</div>}
          <button type="button" className={styles.cancelBtn} onClick={onClose}>キャンセル</button>
          <button
            type="button"
            className={styles.createBtn}
            onClick={handleSave}
            disabled={!name.trim()}
          >
            保存
          </button>
        </div>
      </div>
    </>
  );
}
