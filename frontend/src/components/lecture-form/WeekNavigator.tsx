"use client";

import { BOOKING_START, BOOKING_END } from "@/lib/lectureTypes";
import {
  getWeekStart,
  formatDateShort,
} from "@/lib/lectureUtils";

interface WeekNavigatorProps {
  currentWeekStart: Date;
  onPrev: () => void;
  onNext: () => void;
}

export default function WeekNavigator({
  currentWeekStart,
  onPrev,
  onNext,
}: WeekNavigatorProps) {
  const prevWeekStart = new Date(currentWeekStart);
  prevWeekStart.setDate(prevWeekStart.getDate() - 7);
  const nextWeekStart = new Date(currentWeekStart);
  nextWeekStart.setDate(nextWeekStart.getDate() + 7);

  const weekEnd = new Date(currentWeekStart);
  weekEnd.setDate(weekEnd.getDate() + 6);

  const bookingWeekStart = getWeekStart(BOOKING_START);
  const bookingWeekEnd = getWeekStart(BOOKING_END);

  const canGoPrev = prevWeekStart >= bookingWeekStart;
  const canGoNext = nextWeekStart <= bookingWeekEnd;

  return (
    <div className="flex items-center justify-between">
      <button
        id="week-nav-prev-btn"
        onClick={onPrev}
        disabled={!canGoPrev}
        className="flex items-center gap-1.5 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        前週
      </button>

      <div className="flex flex-col items-center">
        <span className="text-base font-bold text-gray-800">
          {formatDateShort(currentWeekStart)} 〜 {formatDateShort(weekEnd)}
        </span>
        <span className="text-xs text-gray-400 mt-0.5">
          申込期間: 8/1 〜 9/13
        </span>
      </div>

      <button
        id="week-nav-next-btn"
        onClick={onNext}
        disabled={!canGoNext}
        className="flex items-center gap-1.5 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        翌週
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}
