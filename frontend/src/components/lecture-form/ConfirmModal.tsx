"use client";

import { ConfirmType } from "@/lib/lectureTypes";

interface ConfirmModalProps {
  isOpen: boolean;
  type: ConfirmType;
  lectureTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export default function ConfirmModal({
  isOpen,
  type,
  lectureTitle,
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  const isDelete = type === "delete";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      {/* オーバーレイ */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* モーダル本体 */}
      <div className="relative z-10 mx-4 w-full max-w-md rounded-2xl bg-white shadow-2xl">
        {/* ヘッダー */}
        <div
          className={`rounded-t-2xl px-6 pt-6 pb-4 ${
            isDelete
              ? "bg-red-50 border-b border-red-100"
              : "bg-amber-50 border-b border-amber-100"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-full ${
                isDelete ? "bg-red-100" : "bg-amber-100"
              }`}
            >
              {isDelete ? (
                <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              ) : (
                <svg className="h-5 w-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              )}
            </div>
            <h2
              id="confirm-modal-title"
              className={`text-lg font-bold ${isDelete ? "text-red-800" : "text-amber-800"}`}
            >
              {isDelete ? "講座の削除" : "講座の変更"}
            </h2>
          </div>
        </div>

        {/* コンテンツ */}
        <div className="px-6 py-5">
          <p className="text-gray-700 text-sm leading-relaxed">
            {isDelete
              ? "以下の講座を削除してもよろしいですか？"
              : "以下の講座を変更してもよろしいですか？"}
          </p>
          <div className="mt-3 rounded-lg bg-gray-50 px-4 py-3">
            <p className="font-semibold text-gray-900">{lectureTitle}</p>
          </div>
          {isDelete && (
            <p className="mt-3 text-xs text-red-600">
              ⚠️ この操作は取り消せません。
            </p>
          )}
        </div>

        {/* アクションボタン */}
        <div className="flex gap-3 px-6 pb-6">
          <button
            id="confirm-modal-cancel-btn"
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
          >
            キャンセル
          </button>
          <button
            id="confirm-modal-confirm-btn"
            onClick={onConfirm}
            disabled={isLoading}
            className={`flex-1 rounded-xl px-4 py-2.5 text-sm font-bold text-white transition disabled:opacity-50 ${
              isDelete
                ? "bg-red-600 hover:bg-red-700"
                : "bg-amber-500 hover:bg-amber-600"
            }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                処理中...
              </span>
            ) : isDelete ? (
              "削除する"
            ) : (
              "変更する"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
