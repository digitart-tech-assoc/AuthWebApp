// 役割: カテゴリ編集モーダル

"use client";

import { useState } from "react";
import ModalFrame from "./ModalFrame";
import ToggleSwitch from "./ToggleSwitch";
import {
  btnPrimary, btnSecondary, fieldLabel, modalBody, modalCloseBtn, modalErrorMsg, modalFooter,
  modalHeader, modalSubtitle, modalTitle, requiredMark, textInput, toggleDesc, toggleLabel, toggleRow,
} from "./roleStyles";

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
    <ModalFrame onBackdropClick={onClose} size="xl" ariaLabel="カテゴリの編集">
      <div className={modalHeader}>
        <div>
          <h2 className={modalTitle}>カテゴリの編集</h2>
          <p className={modalSubtitle}>カテゴリ名や管理者専用設定を変更します</p>
        </div>
        <button type="button" className={modalCloseBtn} onClick={onClose} aria-label="閉じる">✕</button>
      </div>

      <div className={modalBody}>
        <div className="flex flex-col gap-3">
          <label className={fieldLabel}>カテゴリ名 <span className={requiredMark}>*</span></label>
          <input
            type="text"
            className={textInput}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="カテゴリ名"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter" && name.trim()) handleSave();
            }}
          />

          {isAdmin && (
            <div className={toggleRow}>
              <div>
                <div className={toggleLabel}>管理者専用カテゴリ</div>
                <div className={toggleDesc}>
                  オンにすると、メンバーは自分がこのカテゴリ内のロールを付与・解除できなくなります。
                </div>
              </div>
              <ToggleSwitch
                checked={isRestricted}
                onChange={setIsRestricted}
                ariaLabel="管理者専用カテゴリ"
              />
            </div>
          )}
        </div>
      </div>

      <div className={modalFooter}>
        {!name.trim() && <div className={modalErrorMsg}>カテゴリ名を入力してください</div>}
        <button type="button" className={btnSecondary} onClick={onClose}>キャンセル</button>
        <button
          type="button"
          className={btnPrimary}
          onClick={handleSave}
          disabled={!name.trim()}
        >
          保存
        </button>
      </div>
    </ModalFrame>
  );
}
