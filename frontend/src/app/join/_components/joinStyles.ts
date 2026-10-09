// 役割: 入会手続きフロー（/join/_components）で共通に使う Tailwind CSS クラス（styling-guide.md 準拠）

// ===== カード =====
export const card = "rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6";
export const cardTitle = "mb-2 text-base font-semibold text-slate-900";

// ===== ボタン =====
const btnBase =
  "inline-flex h-10 items-center justify-center rounded-lg px-4 text-sm font-semibold shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";
export const btnPrimary = `${btnBase} bg-blue-600 text-white enabled:hover:bg-blue-700`;
export const btnSecondary = `${btnBase} border border-slate-300 bg-white text-slate-700 enabled:hover:bg-slate-50`;

// ===== アラート =====
const alertBase = "rounded-lg border p-4 text-sm";
export const alertSuccess = `${alertBase} border-emerald-200 bg-emerald-50 text-emerald-700`;
export const alertError = `${alertBase} border-red-200 bg-red-50 text-red-700`;
export const alertWarning = `${alertBase} border-amber-200 bg-amber-50 text-amber-800`;
export const alertInfo = `${alertBase} border-sky-200 bg-sky-50 text-sky-800`;

// ===== テキスト =====
export const textLink = "text-blue-600 underline hover:text-blue-700";
export const fieldLabel = "mb-2 block text-sm font-semibold text-slate-900";
export const fieldError = "text-xs text-red-600";
