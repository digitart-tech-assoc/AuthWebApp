// 役割: ロール管理画面のモーダル共通枠（オーバーレイ + 中央寄せダイアログ）

"use client";

import type { ReactNode } from "react";

const sizeClass = {
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
} as const;

type Props = {
  onBackdropClick: () => void;
  size?: keyof typeof sizeClass;
  /** true の場合、中身の量に関わらず高さを固定する（540px。画面が低い場合は画面内に収める） */
  fixedHeight?: boolean;
  ariaLabel?: string;
  children: ReactNode;
};

export default function ModalFrame({ onBackdropClick, size = "lg", fixedHeight = false, ariaLabel, children }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-10">
      <div className="absolute inset-0 bg-slate-900/50 animate-fade-in" onClick={onBackdropClick} />
      <div
        className={`relative flex max-h-full w-full ${sizeClass[size]} ${fixedHeight ? "h-135" : ""} flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl animate-pop-in`}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
      >
        {children}
      </div>
    </div>
  );
}
