"use client";

import { FormState, UserInfo, Lecture, SLOT_MINUTES, CALENDAR_START_HOUR, CALENDAR_END_HOUR } from "@/lib/lectureTypes";
import {
  generateTimeOptions,
  minutesToTimeString,
  toDateString,
  formatDateHeader,
} from "@/lib/lectureUtils";

interface BookingFormProps {
  form: FormState;
  userInfo: UserInfo | null;
  editingLecture: Lecture | null;
  isSubmitting: boolean;
  error: string | null;
  onFormChange: (updates: Partial<FormState>) => void;
  onSubmit: () => void;
  onCancelEdit: () => void;
}

const TIME_OPTIONS = generateTimeOptions();

/** 終了時間のオプション（開始時間より後のみ） */
function getEndOptions(startMins: number) {
  return TIME_OPTIONS.filter((o) => o.value > startMins);
}

export default function BookingForm({
  form,
  userInfo,
  editingLecture,
  isSubmitting,
  error,
  onFormChange,
  onSubmit,
  onCancelEdit,
}: BookingFormProps) {
  const isEdit = !!editingLecture;

  // 選択中の日付オブジェクト（表示用）
  const selectedDateObj = form.date
    ? (() => {
        const [y, m, d] = form.date.split("-").map(Number);
        return new Date(y, m - 1, d);
      })()
    : null;

  const durationMins = form.endMinutes - form.startMinutes;
  const durationDisplay =
    durationMins > 0
      ? `${Math.floor(durationMins / 60) > 0 ? Math.floor(durationMins / 60) + "時間" : ""}${durationMins % 60 > 0 ? (durationMins % 60) + "分" : ""}`
      : null;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      {/* ヘッダー */}
      <div className="border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-gray-800">
              {isEdit ? "📝 講座を編集" : "✏️ 新規申し込み"}
            </h2>
            {form.date && (
              <p className="mt-0.5 text-xs text-gray-500">
                {selectedDateObj ? formatDateHeader(selectedDateObj) : form.date} ·{" "}
                {minutesToTimeString(form.startMinutes)} 〜 {minutesToTimeString(form.endMinutes)}
                {durationDisplay && (
                  <span className="ml-1.5 rounded-full bg-indigo-50 px-2 py-0.5 text-indigo-600 font-medium">
                    {durationDisplay}
                  </span>
                )}
              </p>
            )}
          </div>
          {isEdit && (
            <button
              id="cancel-edit-btn"
              onClick={onCancelEdit}
              className="rounded-xl border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50"
            >
              新規作成に戻す
            </button>
          )}
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* エラー表示 */}
        {error && (
          <div className="flex items-start gap-2 rounded-xl bg-red-50 border border-red-200 px-4 py-3">
            <svg className="h-4 w-4 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Discord名 */}
        <div>
          <label htmlFor="form-discord-name" className="block text-xs font-semibold text-gray-600 mb-1.5">
            Discord名 <span className="text-red-500">*</span>
            {userInfo?.discordName && (
              <span className="ml-2 rounded-full bg-indigo-100 px-2 py-0.5 text-indigo-600 text-[10px] font-medium">
                ログイン済み（自動入力）
              </span>
            )}
          </label>
          <input
            id="form-discord-name"
            type="text"
            value={form.discordName}
            onChange={(e) => onFormChange({ discordName: e.target.value })}
            disabled={!!userInfo?.discordName}
            placeholder="あなたのDiscord名"
            className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-800 transition focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:opacity-60"
          />
        </div>

        {/* 講座タイトル */}
        <div>
          <label htmlFor="form-title" className="block text-xs font-semibold text-gray-600 mb-1.5">
            講座タイトル <span className="text-red-500">*</span>
          </label>
          <input
            id="form-title"
            type="text"
            value={form.title}
            onChange={(e) => onFormChange({ title: e.target.value })}
            placeholder="例: Webデザイン入門"
            className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-800 transition focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
        </div>

        {/* 日時選択 */}
        <div>
          <p className="block text-xs font-semibold text-gray-600 mb-1.5">
            開催日時 <span className="text-red-500">*</span>
            <span className="ml-1 font-normal text-gray-400">（カレンダーでドラッグするか、以下で調整）</span>
          </p>
          <div className="grid grid-cols-3 gap-2">
            {/* 日付 */}
            <div>
              <label htmlFor="form-date" className="block text-[10px] text-gray-400 mb-1">日付</label>
              <input
                id="form-date"
                type="date"
                value={form.date}
                min="2026-08-01"
                max="2026-09-13"
                onChange={(e) => onFormChange({ date: e.target.value })}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-gray-800 transition focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            {/* 開始時間 */}
            <div>
              <label htmlFor="form-start-time" className="block text-[10px] text-gray-400 mb-1">開始時間</label>
              <select
                id="form-start-time"
                value={form.startMinutes}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  onFormChange({
                    startMinutes: val,
                    endMinutes: Math.max(form.endMinutes, val + SLOT_MINUTES),
                  });
                }}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-gray-800 transition focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
              >
                {TIME_OPTIONS.filter((o) => o.value < CALENDAR_END_HOUR * 60).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 終了時間 */}
            <div>
              <label htmlFor="form-end-time" className="block text-[10px] text-gray-400 mb-1">終了時間</label>
              <select
                id="form-end-time"
                value={form.endMinutes}
                onChange={(e) => onFormChange({ endMinutes: Number(e.target.value) })}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-gray-800 transition focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
              >
                {getEndOptions(form.startMinutes).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 備考 */}
        <div>
          <label htmlFor="form-notes" className="block text-xs font-semibold text-gray-600 mb-1.5">
            その他・備考 <span className="text-gray-400 font-normal">（任意）</span>
          </label>
          <textarea
            id="form-notes"
            rows={3}
            value={form.notes}
            onChange={(e) => onFormChange({ notes: e.target.value })}
            placeholder="必要な機材、参加人数の目安など"
            className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-800 transition focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100 resize-none"
          />
        </div>

        {/* 未ログイン注意文 */}
        {!userInfo && (
          <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
            <svg className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-xs text-amber-700">
              未ログインで申し込むと、後からの変更・削除は管理者に依頼が必要になります。
              <a href="/login" className="underline font-medium ml-1">Discordでログイン</a>すると自分で管理できます。
            </p>
          </div>
        )}

        {/* 送信ボタン */}
        <button
          id="form-submit-btn"
          onClick={onSubmit}
          disabled={isSubmitting || !form.title || !form.discordName || !form.date}
          className="w-full rounded-xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-indigo-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              送信中...
            </span>
          ) : isEdit ? (
            "変更を保存する"
          ) : (
            "申し込む"
          )}
        </button>
      </div>
    </div>
  );
}
