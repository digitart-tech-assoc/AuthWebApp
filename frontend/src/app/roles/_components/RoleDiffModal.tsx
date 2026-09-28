"use client";

import type { ReactNode } from "react";
import type { RoleDiffData } from "@/types/roles";
import ModalFrame from "./ModalFrame";
import { btnPrimary, btnSecondary, modalFooter, modalSubtitle } from "./roleStyles";

interface Props {
  diffData: RoleDiffData;
  onClose: () => void;
  onConfirm: () => void;
}

const detailClass = "ml-3 text-xs text-slate-500";

function DiffSection({ titleClass, title, children }: { titleClass: string; title: string; children: ReactNode }) {
  return (
    <div className="mb-4">
      <div className={`mb-2 font-bold ${titleClass}`}>{title}</div>
      <ul className="m-0 ml-5 list-disc pl-0">{children}</ul>
    </div>
  );
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
    <ModalFrame onBackdropClick={onClose} size="xl" ariaLabel="変更内容確認">
      <div className="flex shrink-0 flex-col gap-1 border-b border-slate-200 px-6 pt-6 pb-4">
        <p className="m-0 text-lg font-bold text-slate-900">変更内容の確認</p>
        <p className={modalSubtitle}>以下の変更をDBに保存し、Discordへ同期します</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-5 text-sm text-slate-700">
        {hasChanges ? (
          <>
            {diffData.roleAdded.length > 0 && (
              <DiffSection titleClass="text-emerald-700" title={`＋ ロールを追加（${diffData.roleAdded.length}件）`}>
                {diffData.roleAdded.map((item) => (
                  <li key={item.role.role_id}>
                    <strong>{item.role.name}</strong>
                    {item.memberCount > 0 && (
                      <div className={detailClass}>👥 {item.memberCount}名割り当て</div>
                    )}
                  </li>
                ))}
              </DiffSection>
            )}

            {diffData.memberAssigned.length > 0 && (
              <DiffSection titleClass="text-violet-700" title={`👥 メンバーを割り当て（${diffData.memberAssigned.length}件）`}>
                {diffData.memberAssigned.map((change) => (
                  <li key={change.roleId}>
                    <strong>{change.roleName}</strong>
                    {change.added.length > 0 && (
                      <div className="ml-3 text-emerald-700">➕ {change.added.length}名追加</div>
                    )}
                    {change.removed.length > 0 && (
                      <div className="ml-3 text-red-700">➖ {change.removed.length}名削除</div>
                    )}
                  </li>
                ))}
              </DiffSection>
            )}

            {diffData.permissionEdited.length > 0 && (
              <DiffSection titleClass="text-amber-700" title={`🔒 権限を編集（${diffData.permissionEdited.length}件）`}>
                {diffData.permissionEdited.map((item) => (
                  <li key={item.roleId}>
                    <strong>{item.roleName}</strong>
                    <div className={detailClass}>
                      {item.oldPermissions} → {item.newPermissions}
                    </div>
                  </li>
                ))}
              </DiffSection>
            )}

            {diffData.orderChanged.length > 0 && (
              <DiffSection titleClass="text-blue-700" title={`📍 表示する順番を変更（${diffData.orderChanged.length}件）`}>
                {diffData.orderChanged.map((item) => (
                  <li key={item.roleId}>
                    <strong>{item.roleName}</strong>
                    <div className={detailClass}>
                      位置: {item.oldPosition} → {item.newPosition}
                    </div>
                  </li>
                ))}
              </DiffSection>
            )}

            {diffData.roleDeleted.length > 0 && (
              <DiffSection titleClass="text-red-700" title={`✕ ロール削除（${diffData.roleDeleted.length}件）`}>
                {diffData.roleDeleted.map((r) => (
                  <li key={r.role_id}>{r.name}</li>
                ))}
              </DiffSection>
            )}

            {diffData.categoriesAdded.length > 0 && (
              <DiffSection titleClass="text-emerald-700" title={`＋ カテゴリ追加（${diffData.categoriesAdded.length}件）`}>
                {diffData.categoriesAdded.map((c) => (
                  <li key={c.id}>{c.name}</li>
                ))}
              </DiffSection>
            )}

            {diffData.categoriesDeleted.length > 0 && (
              <DiffSection titleClass="text-red-700" title={`✕ カテゴリ削除（${diffData.categoriesDeleted.length}件）`}>
                {diffData.categoriesDeleted.map((c) => (
                  <li key={c.id}>{c.name}</li>
                ))}
              </DiffSection>
            )}
          </>
        ) : (
          <p className="text-slate-500">変更がありません</p>
        )}
      </div>
      <div className={modalFooter}>
        <button type="button" className={btnSecondary} onClick={onClose}>
          キャンセル
        </button>
        <button type="button" className={btnPrimary} onClick={onConfirm}>
          保存してDiscordへ送信
        </button>
      </div>
    </ModalFrame>
  );
}
