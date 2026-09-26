// 役割: ロール管理画面（/roles）の複数コンポーネントで共有する Tailwind クラス定義

// ===== ボタン =====
const btnBase =
  "inline-flex h-10 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg px-4 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export const btnPrimary = `${btnBase} bg-blue-600 font-semibold text-white shadow-sm hover:bg-blue-700`;
export const btnSecondary = `${btnBase} border border-slate-300 bg-white font-medium text-slate-700 shadow-sm hover:bg-slate-50`;
export const btnSync = `${btnBase} bg-slate-600 font-semibold text-white shadow-sm hover:bg-slate-700`;

// ===== モーダル内の共通パーツ =====
export const modalHeader = "flex shrink-0 items-start justify-between gap-3 px-6 pt-5";
export const modalTitle = "m-0 text-base font-bold text-slate-900";
export const modalSubtitle = "mt-1 mb-0 text-xs text-slate-500";
export const modalBody = "min-h-0 flex-1 overflow-y-auto px-6 py-4";
export const modalFooter =
  "flex shrink-0 flex-wrap items-center justify-end gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4";
export const modalCloseBtn =
  "inline-flex size-10 shrink-0 items-center justify-center rounded-lg text-base leading-none text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
export const modalErrorMsg = "flex-1 text-xs font-medium text-red-600";

// ===== フォーム =====
export const fieldLabel = "-mb-1 text-xs font-bold uppercase tracking-wider text-slate-500";
export const requiredMark = "text-red-600";
export const textInput =
  "block h-10 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20";
export const selectInput = `${textInput} cursor-pointer`;

// ===== トグル行 =====
export const toggleRow = "flex items-center justify-between gap-3 border-t border-slate-200 py-2";
export const toggleLabel = "text-sm font-medium text-slate-900";
export const toggleDesc = "mt-0.5 text-xs text-slate-500";
