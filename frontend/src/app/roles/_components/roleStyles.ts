// 役割: ロール管理画面（/roles）の複数コンポーネントで共有する Tailwind クラス定義

// ===== ボタン =====
const btnBase =
  "inline-flex h-10 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg px-4 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export const btnPrimary = `${btnBase} bg-blue-600 font-semibold text-white shadow-sm hover:bg-blue-700`;
export const btnSecondary = `${btnBase} border border-slate-300 bg-white font-medium text-slate-700 shadow-sm hover:bg-slate-50`;
export const btnSync = `${btnBase} bg-slate-600 font-semibold text-white shadow-sm hover:bg-slate-700`;
export const btnCreate = `${btnBase} bg-emerald-600 font-semibold text-white shadow-sm hover:bg-emerald-700`;
export const btnDanger = `${btnBase} border border-red-300 bg-white font-semibold text-red-700 hover:bg-red-50`;

// 行内コンパクトボタン（styling-guide.md「行内コンパクトボタン」参照）
export const btnCompact =
  "inline-flex h-8 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border px-2.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50";

// ===== ステータス表示 =====
const statusBannerKind = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  error: "border-red-200 bg-red-50 text-red-700",
  info: "border-sky-200 bg-sky-50 text-sky-800",
} as const;

export const statusBanner = (kind: keyof typeof statusBannerKind) =>
  `mb-4 flex items-center gap-2 rounded-lg border px-3.5 py-2.5 text-sm font-medium animate-fade-in-down ${statusBannerKind[kind]}`;

// 画面下部に浮かぶ「未送信の変更があります」バー
export const unsavedBar =
  "fixed inset-x-4 bottom-6 z-40 mx-auto flex w-fit max-w-full flex-wrap items-center justify-center gap-3 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-medium text-white shadow-xl animate-slide-up";
export const unsavedBarBtn =
  "inline-flex h-10 items-center whitespace-nowrap rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-60";

// ===== カテゴリグループ（アコーディオン） =====
export const groupCard = "overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm";
export const groupHeader =
  "group flex min-h-12 cursor-pointer select-none items-center gap-2 border-b border-slate-100 bg-slate-50 px-3.5 py-2 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500";
export const groupName = "min-w-0 flex-1 truncate text-xs font-bold uppercase tracking-wider text-slate-600";
export const groupCount = "rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600";
export const chevron = (open: boolean) =>
  `size-4 shrink-0 text-slate-400 transition-transform ${open ? "rotate-90" : ""}`;

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
