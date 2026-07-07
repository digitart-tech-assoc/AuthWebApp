"use client";

import { Lecture, UserInfo, CALENDAR_START_HOUR, CALENDAR_END_HOUR } from "@/lib/lectureTypes";
import {
  isoToMinutes,
  minutesToTimeString,
  minutesToPercent,
  formatTimeRange,
  isoToDateString,
} from "@/lib/lectureUtils";

interface LectureBlockProps {
  lecture: Lecture;
  userInfo: UserInfo | null;
  dateStr: string;
  onEdit: (lecture: Lecture) => void;
  onDelete: (lecture: Lecture) => void;
}

export default function LectureBlock({
  lecture,
  userInfo,
  dateStr,
  onEdit,
  onDelete,
}: LectureBlockProps) {
  if (isoToDateString(lecture.start_at) !== dateStr) return null;

  const startMins = isoToMinutes(lecture.start_at);
  const endMins = isoToMinutes(lecture.end_at);
  const topPercent = minutesToPercent(startMins) * 100;
  const heightPercent = minutesToPercent(endMins) * 100 - topPercent;

  const durationMins = endMins - startMins;

  // 権限チェック
  const isOwner = userInfo && lecture.user_id === userInfo.id;
  const canEdit = userInfo?.isAdmin || isOwner;

  return (
    <div
      className="absolute left-0.5 right-0.5 z-10 flex flex-col overflow-hidden rounded-lg border border-indigo-300 bg-indigo-100/90 px-1.5 py-1 shadow-sm transition-shadow hover:shadow-md"
      style={{
        top: `${topPercent}%`,
        height: `${Math.max(heightPercent, 2)}%`,
      }}
      title={`${lecture.title} | ${lecture.discord_name} | ${formatTimeRange(lecture.start_at, lecture.end_at)}`}
    >
      {/* タイトル */}
      <p className="truncate text-xs font-bold leading-tight text-indigo-900">
        {lecture.title}
      </p>

      {/* 時間（高さが十分な場合のみ表示） */}
      {durationMins >= 40 && (
        <p className="truncate text-[10px] leading-tight text-indigo-700">
          {minutesToTimeString(startMins)}〜{minutesToTimeString(endMins)}
        </p>
      )}

      {/* Discord名（高さが十分な場合のみ表示） */}
      {durationMins >= 60 && (
        <p className="truncate text-[10px] leading-tight text-indigo-600">
          @{lecture.discord_name}
        </p>
      )}

      {/* 編集・削除ボタン（権限がある場合のみ） */}
      {canEdit && (
        <div className="mt-auto flex gap-1 pt-0.5">
          <button
            id={`lecture-edit-btn-${lecture.id}`}
            onClick={(e) => {
              e.stopPropagation();
              onEdit(lecture);
            }}
            className="flex-1 rounded bg-indigo-200 px-1 py-0.5 text-[9px] font-bold text-indigo-800 transition hover:bg-indigo-300"
            title="編集"
          >
            編集
          </button>
          <button
            id={`lecture-delete-btn-${lecture.id}`}
            onClick={(e) => {
              e.stopPropagation();
              onDelete(lecture);
            }}
            className="flex-1 rounded bg-red-200 px-1 py-0.5 text-[9px] font-bold text-red-800 transition hover:bg-red-300"
            title="削除"
          >
            削除
          </button>
        </div>
      )}
    </div>
  );
}

/** カレンダー外部の講座リスト表示用（コンパクト版） */
export function LectureListItem({
  lecture,
  userInfo,
  onEdit,
  onDelete,
}: {
  lecture: Lecture;
  userInfo: UserInfo | null;
  onEdit: (lecture: Lecture) => void;
  onDelete: (lecture: Lecture) => void;
}) {
  const startMins = isoToMinutes(lecture.start_at);
  const endMins = isoToMinutes(lecture.end_at);
  const isOwner = userInfo && lecture.user_id === userInfo.id;
  const canEdit = userInfo?.isAdmin || isOwner;

  // 日付取得
  const dateObj = new Date(lecture.start_at);
  const jst = new Date(dateObj.getTime() + 9 * 60 * 60 * 1000);
  const month = jst.getUTCMonth() + 1;
  const day = jst.getUTCDate();
  const dayNames = ["日", "月", "火", "水", "木", "金", "土"];
  const dow = dayNames[jst.getUTCDay()];

  return (
    <div className="flex items-center justify-between rounded-xl border border-indigo-100 bg-indigo-50/60 px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="truncate font-semibold text-indigo-900 text-sm">{lecture.title}</p>
        <p className="text-xs text-indigo-600 mt-0.5">
          {month}/{day}({dow}) {minutesToTimeString(startMins)}〜{minutesToTimeString(endMins)} ·{" "}
          <span className="text-gray-500">@{lecture.discord_name}</span>
        </p>
      </div>
      {canEdit && (
        <div className="flex gap-2 ml-3 shrink-0">
          <button
            id={`lecture-list-edit-btn-${lecture.id}`}
            onClick={() => onEdit(lecture)}
            className="rounded-lg bg-indigo-100 px-3 py-1 text-xs font-bold text-indigo-800 transition hover:bg-indigo-200"
          >
            編集
          </button>
          <button
            id={`lecture-list-delete-btn-${lecture.id}`}
            onClick={() => onDelete(lecture)}
            className="rounded-lg bg-red-100 px-3 py-1 text-xs font-bold text-red-800 transition hover:bg-red-200"
          >
            削除
          </button>
        </div>
      )}
    </div>
  );
}
