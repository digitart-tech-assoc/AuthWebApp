"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import {
  Lecture,
  UserInfo,
  DragSelection,
  CALENDAR_START_HOUR,
  CALENDAR_END_HOUR,
  SLOT_MINUTES,
  BOOKING_START,
  BOOKING_END,
} from "@/lib/lectureTypes";
import {
  getWeekDays,
  generateHourSlots,
  minutesToTimeString,
  minutesToPercent,
  snapToSlot,
  pixelToMinutes,
  toDateString,
  hasOverlap,
  getLecturesForDate,
  formatDateHeader,
  DAY_NAMES_JA,
} from "@/lib/lectureUtils";
import LectureBlock from "./LectureBlock";

interface WeeklyCalendarProps {
  weekStart: Date;
  lectures: Lecture[];
  dragSelection: DragSelection | null;
  userInfo: UserInfo | null;
  onSelectionChange: (sel: DragSelection | null) => void;
  onEditLecture: (lecture: Lecture) => void;
  onDeleteLecture: (lecture: Lecture) => void;
}

const HOUR_SLOTS = generateHourSlots();
const TOTAL_MINUTES = (CALENDAR_END_HOUR - CALENDAR_START_HOUR) * 60;

export default function WeeklyCalendar({
  weekStart,
  lectures,
  dragSelection,
  userInfo,
  onSelectionChange,
  onEditLecture,
  onDeleteLecture,
}: WeeklyCalendarProps) {
  const weekDays = getWeekDays(weekStart);

  // ドラッグ状態
  const dragging = useRef(false);
  const dragStartMins = useRef(0);
  const dragDateStr = useRef("");
  const gridRef = useRef<HTMLDivElement>(null);

  // 各列の ref（ドラッグ計算に使用）
  const columnRefs = useRef<(HTMLDivElement | null)[]>([]);

  /** マウスY座標 → 分数変換 */
  const getMinutesFromMouseY = useCallback((y: number, colEl: HTMLDivElement): number => {
    const rect = colEl.getBoundingClientRect();
    const relY = y - rect.top;
    return pixelToMinutes(relY, rect.height);
  }, []);

  /** ドラッグ開始 */
  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>, dateStr: string, colIndex: number) => {
      e.preventDefault();

      const colEl = columnRefs.current[colIndex];
      if (!colEl) return;

      // 期間外は無視
      const [y, mo, d] = dateStr.split("-").map(Number);
      const dateObj = new Date(y, mo - 1, d);
      if (dateObj < BOOKING_START || dateObj > BOOKING_END) return;

      const startMins = getMinutesFromMouseY(e.clientY, colEl);

      dragging.current = true;
      dragStartMins.current = startMins;
      dragDateStr.current = dateStr;

      onSelectionChange({
        date: dateStr,
        startMinutes: startMins,
        endMinutes: Math.min(startMins + SLOT_MINUTES, CALENDAR_END_HOUR * 60),
      });
    },
    [getMinutesFromMouseY, onSelectionChange]
  );

  /** ドラッグ中 */
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!dragging.current) return;

      const colIndex = weekDays.findIndex((d) => toDateString(d) === dragDateStr.current);
      const colEl = columnRefs.current[colIndex];
      if (!colEl) return;

      const currentMins = getMinutesFromMouseY(e.clientY, colEl);
      const rawStart = Math.min(dragStartMins.current, currentMins);
      const rawEnd = Math.max(dragStartMins.current, currentMins);

      const snappedStart = snapToSlot(rawStart);
      const snappedEnd = Math.max(snapToSlot(rawEnd), snappedStart + SLOT_MINUTES);

      onSelectionChange({
        date: dragDateStr.current,
        startMinutes: snappedStart,
        endMinutes: Math.min(snappedEnd, CALENDAR_END_HOUR * 60),
      });
    },
    [getMinutesFromMouseY, onSelectionChange, weekDays]
  );

  /** ドラッグ終了 */
  const handleMouseUp = useCallback(() => {
    dragging.current = false;
  }, []);

  // グローバルイベントリスナー
  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* 凡例 */}
      <div className="flex items-center gap-4 border-b border-gray-100 px-4 py-2.5 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <div className="h-3.5 w-3.5 rounded bg-indigo-200 border border-indigo-300" />
          <span>予約済み</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-3.5 w-3.5 rounded bg-emerald-200 border border-emerald-300" />
          <span>選択中</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-3.5 w-3.5 rounded bg-gray-100 border border-gray-200" />
          <span>空き</span>
        </div>
        <div className="ml-auto text-gray-400 hidden sm:block">
          ドラッグして時間帯を選択
        </div>
      </div>

      {/* カレンダーグリッド */}
      <div className="flex" ref={gridRef}>
        {/* 時間軸（左端） */}
        <div className="w-12 shrink-0 border-r border-gray-100">
          {/* 曜日ヘッダー分の高さ確保 */}
          <div className="h-10 border-b border-gray-100" />
          {/* 時間目盛り */}
          <div className="relative" style={{ height: `${TOTAL_MINUTES * 1.5}px` }}>
            {HOUR_SLOTS.map((mins) => (
              <div
                key={mins}
                className="absolute left-0 right-0 flex items-start justify-end pr-2"
                style={{ top: `${minutesToPercent(mins) * 100}%` }}
              >
                <span className="text-[10px] text-gray-400 -translate-y-2">
                  {minutesToTimeString(mins)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 日付カラム群 */}
        <div className="flex flex-1 min-w-0 overflow-x-auto">
          {weekDays.map((day, colIndex) => {
            const dateStr = toDateString(day);
            const isInPeriod = day >= BOOKING_START && day <= BOOKING_END;
            const isToday = toDateString(new Date()) === dateStr;
            const dayLectures = getLecturesForDate(lectures, dateStr);

            const dow = day.getDay(); // 0=Sun, 6=Sat
            const isSat = dow === 6;
            const isSun = dow === 0;

            return (
              <div
                key={dateStr}
                className="flex flex-col border-r border-gray-100 last:border-r-0"
                style={{ minWidth: "80px", flex: "1 0 0" }}
              >
                {/* 曜日ヘッダー */}
                <div
                  className={`flex h-10 flex-col items-center justify-center border-b border-gray-100 text-xs font-semibold ${
                    isToday
                      ? "bg-indigo-600 text-white"
                      : isSat
                      ? "text-blue-600 bg-blue-50"
                      : isSun
                      ? "text-red-600 bg-red-50"
                      : "text-gray-700 bg-gray-50"
                  } ${!isInPeriod ? "opacity-40" : ""}`}
                >
                  <span className="text-[10px] leading-none">
                    {DAY_NAMES_JA[dow === 0 ? 6 : dow - 1]}
                  </span>
                  <span className="text-xs leading-tight">
                    {day.getMonth() + 1}/{day.getDate()}
                  </span>
                </div>

                {/* 時間グリッド */}
                <div
                  ref={(el) => { columnRefs.current[colIndex] = el; }}
                  className={`relative select-none ${
                    isInPeriod
                      ? "cursor-crosshair hover:bg-indigo-50/20"
                      : "cursor-not-allowed bg-gray-50/60"
                  }`}
                  style={{ height: `${TOTAL_MINUTES * 1.5}px` }}
                  onMouseDown={
                    isInPeriod
                      ? (e) => handleMouseDown(e, dateStr, colIndex)
                      : undefined
                  }
                >
                  {/* 時間グリッドライン */}
                  {HOUR_SLOTS.map((mins) => (
                    <div
                      key={mins}
                      className="absolute left-0 right-0 border-t border-gray-100"
                      style={{ top: `${minutesToPercent(mins) * 100}%` }}
                    />
                  ))}

                  {/* 30分グリッドライン（薄く） */}
                  {HOUR_SLOTS.slice(0, -1).map((mins) => (
                    <div
                      key={`${mins}-half`}
                      className="absolute left-0 right-0 border-t border-gray-50"
                      style={{ top: `${minutesToPercent(mins + 30) * 100}%` }}
                    />
                  ))}

                  {/* 期間外オーバーレイ */}
                  {!isInPeriod && (
                    <div className="absolute inset-0 bg-gray-100/40 z-5" />
                  )}

                  {/* 現在時刻ライン（今日のみ） */}
                  {isToday && (() => {
                    const now = new Date();
                    const nowMins = now.getHours() * 60 + now.getMinutes();
                    if (nowMins >= CALENDAR_START_HOUR * 60 && nowMins <= CALENDAR_END_HOUR * 60) {
                      return (
                        <div
                          className="absolute left-0 right-0 z-20 border-t-2 border-red-400"
                          style={{ top: `${minutesToPercent(nowMins) * 100}%` }}
                        >
                          <div className="absolute -top-1 left-0 h-2 w-2 rounded-full bg-red-400" />
                        </div>
                      );
                    }
                    return null;
                  })()}

                  {/* 予約済み講座ブロック */}
                  {dayLectures.map((lec) => (
                    <LectureBlock
                      key={lec.id}
                      lecture={lec}
                      userInfo={userInfo}
                      dateStr={dateStr}
                      onEdit={onEditLecture}
                      onDelete={onDeleteLecture}
                    />
                  ))}

                  {/* ドラッグ選択ハイライト */}
                  {dragSelection && dragSelection.date === dateStr && (() => {
                    const isOverlap = hasOverlap(
                      lectures,
                      dateStr,
                      dragSelection.startMinutes,
                      dragSelection.endMinutes
                    );
                    const topPct = minutesToPercent(dragSelection.startMinutes) * 100;
                    const heightPct =
                      minutesToPercent(dragSelection.endMinutes) * 100 - topPct;

                    return (
                      <div
                        className={`absolute left-0.5 right-0.5 z-20 rounded-lg border-2 transition-colors ${
                          isOverlap
                            ? "border-red-400 bg-red-100/80"
                            : "border-emerald-400 bg-emerald-100/80"
                        }`}
                        style={{
                          top: `${topPct}%`,
                          height: `${Math.max(heightPct, 1.5)}%`,
                        }}
                      >
                        <div
                          className={`absolute -top-5 left-0 rounded px-1 py-0.5 text-[10px] font-bold whitespace-nowrap ${
                            isOverlap ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {isOverlap
                            ? "⚠️ 重複"
                            : `${minutesToTimeString(dragSelection.startMinutes)} - ${minutesToTimeString(dragSelection.endMinutes)}`}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* フッター説明 */}
      <div className="border-t border-gray-100 px-4 py-2 text-xs text-gray-400 text-center">
        カレンダーをドラッグして希望の時間帯を選択してください。下のフォームから微調整もできます。
      </div>
    </div>
  );
}
