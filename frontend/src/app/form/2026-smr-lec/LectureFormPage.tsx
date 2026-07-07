"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Lecture,
  UserInfo,
  DragSelection,
  FormState,
  ConfirmType,
  BOOKING_START,
  CALENDAR_START_HOUR,
  SLOT_MINUTES,
} from "@/lib/lectureTypes";
import {
  getWeekStart,
  toDateString,
  toISOStringFromDateAndMinutes,
  isoToMinutes,
  isoToDateString,
  hasOverlap,
} from "@/lib/lectureUtils";
import WeeklyCalendar from "@/components/lecture-form/WeeklyCalendar";
import WeekNavigator from "@/components/lecture-form/WeekNavigator";
import BookingForm from "@/components/lecture-form/BookingForm";
import ConfirmModal from "@/components/lecture-form/ConfirmModal";
import { LectureListItem } from "@/components/lecture-form/LectureBlock";

interface LectureFormPageProps {
  userInfo: UserInfo | null;
}

const DEFAULT_START_MINS = 10 * 60; // 10:00
const DEFAULT_END_MINS = DEFAULT_START_MINS + SLOT_MINUTES * 3; // 11:00

function getDefaultDate(): string {
  const today = new Date();
  const todayStr = toDateString(today);
  const bookingStartStr = toDateString(BOOKING_START);
  return todayStr >= bookingStartStr ? todayStr : bookingStartStr;
}

export default function LectureFormPage({ userInfo }: LectureFormPageProps) {
  // ============================================================
  // 状態管理
  // ============================================================
  const [weekStart, setWeekStart] = useState<Date>(() =>
    getWeekStart(
      new Date() >= BOOKING_START ? new Date() : BOOKING_START
    )
  );
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [isLoadingLectures, setIsLoadingLectures] = useState(true);
  const [dragSelection, setDragSelection] = useState<DragSelection | null>(null);
  const [editingLecture, setEditingLecture] = useState<Lecture | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 確認ダイアログ
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmType, setConfirmType] = useState<ConfirmType>("delete");
  const [confirmTarget, setConfirmTarget] = useState<Lecture | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  // フォーム状態
  const [form, setForm] = useState<FormState>({
    title: "",
    discordName: userInfo?.discordName ?? "",
    date: getDefaultDate(),
    startMinutes: DEFAULT_START_MINS,
    endMinutes: DEFAULT_END_MINS,
    notes: "",
  });

  // ============================================================
  // 講座データ取得
  // ============================================================
  const fetchLectures = useCallback(async () => {
    try {
      setIsLoadingLectures(true);
      const res = await fetch("/api/lectures", { cache: "no-store" });
      if (!res.ok) throw new Error("fetch failed");
      const { lectures: data } = await res.json();
      setLectures(data);
    } catch {
      console.error("Failed to fetch lectures");
    } finally {
      setIsLoadingLectures(false);
    }
  }, []);

  useEffect(() => {
    fetchLectures();
  }, [fetchLectures]);

  // ============================================================
  // ドラッグ選択 → フォーム同期
  // ============================================================
  const handleSelectionChange = useCallback(
    (sel: DragSelection | null) => {
      setDragSelection(sel);
      if (sel) {
        setForm((prev) => ({
          ...prev,
          date: sel.date,
          startMinutes: sel.startMinutes,
          endMinutes: sel.endMinutes,
        }));
        setSubmitError(null);
      }
    },
    []
  );

  // ============================================================
  // フォーム変更 → ドラッグ選択同期
  // ============================================================
  const handleFormChange = useCallback((updates: Partial<FormState>) => {
    setForm((prev) => {
      const next = { ...prev, ...updates };
      setDragSelection({
        date: next.date,
        startMinutes: next.startMinutes,
        endMinutes: next.endMinutes,
      });
      return next;
    });
    setSubmitError(null);
  }, []);

  // ============================================================
  // 週ナビゲーション
  // ============================================================
  const handlePrevWeek = useCallback(() => {
    setWeekStart((prev) => {
      const d = new Date(prev);
      d.setDate(d.getDate() - 7);
      return d;
    });
  }, []);

  const handleNextWeek = useCallback(() => {
    setWeekStart((prev) => {
      const d = new Date(prev);
      d.setDate(d.getDate() + 7);
      return d;
    });
  }, []);

  // ============================================================
  // 編集モード開始
  // ============================================================
  const handleEditLecture = useCallback(
    (lecture: Lecture) => {
      setEditingLecture(lecture);
      const startMins = isoToMinutes(lecture.start_at);
      const endMins = isoToMinutes(lecture.end_at);
      const dateStr = isoToDateString(lecture.start_at);
      setForm({
        title: lecture.title,
        discordName: lecture.discord_name,
        date: dateStr,
        startMinutes: startMins,
        endMinutes: endMins,
        notes: lecture.notes ?? "",
      });
      setDragSelection({ date: dateStr, startMinutes: startMins, endMinutes: endMins });
      setSubmitError(null);
      setSuccessMsg(null);
      // フォームまでスクロール
      document.getElementById("booking-form-section")?.scrollIntoView({ behavior: "smooth" });
    },
    []
  );

  const handleCancelEdit = useCallback(() => {
    setEditingLecture(null);
    setForm({
      title: "",
      discordName: userInfo?.discordName ?? "",
      date: getDefaultDate(),
      startMinutes: DEFAULT_START_MINS,
      endMinutes: DEFAULT_END_MINS,
      notes: "",
    });
    setDragSelection(null);
    setSubmitError(null);
  }, [userInfo]);

  // ============================================================
  // 削除確認ダイアログ
  // ============================================================
  const handleDeleteRequest = useCallback((lecture: Lecture) => {
    setConfirmTarget(lecture);
    setConfirmType("delete");
    setConfirmOpen(true);
  }, []);

  const handleUpdateRequest = useCallback(() => {
    if (!editingLecture) return;
    setConfirmTarget(editingLecture);
    setConfirmType("update");
    setConfirmOpen(true);
  }, [editingLecture]);

  // ============================================================
  // 送信処理
  // ============================================================
  const handleSubmit = useCallback(async () => {
    setSubmitError(null);

    // バリデーション
    if (!form.title.trim()) {
      setSubmitError("講座タイトルを入力してください");
      return;
    }
    if (!form.discordName.trim()) {
      setSubmitError("Discord名を入力してください");
      return;
    }
    if (!form.date) {
      setSubmitError("日付を選択してください");
      return;
    }
    if (form.endMinutes <= form.startMinutes) {
      setSubmitError("終了時刻は開始時刻より後にしてください");
      return;
    }

    // 重複チェック（フロント側）
    const overlap = hasOverlap(
      lectures,
      form.date,
      form.startMinutes,
      form.endMinutes,
      editingLecture?.id
    );
    if (overlap) {
      setSubmitError("選択した時間帯はすでに予約されています。別の時間帯を選択してください。");
      return;
    }

    // 編集の場合は確認ダイアログを挟む
    if (editingLecture) {
      handleUpdateRequest();
      return;
    }

    // 新規作成
    await executeSubmit();
  }, [form, lectures, editingLecture, handleUpdateRequest]);

  const executeSubmit = useCallback(async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const start_at = toISOStringFromDateAndMinutes(form.date, form.startMinutes);
      const end_at = toISOStringFromDateAndMinutes(form.date, form.endMinutes);

      const res = await fetch("/api/lectures", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: form.title,
          discord_name: form.discordName,
          start_at,
          end_at,
          notes: form.notes || null,
        }),
      });

      const body = await res.json();
      if (!res.ok) {
        setSubmitError(body.error ?? "申し込みに失敗しました");
        return;
      }

      setSuccessMsg("申し込みが完了しました！🎉");
      await fetchLectures();
      handleCancelEdit();
    } catch {
      setSubmitError("ネットワークエラーが発生しました。再度お試しください。");
    } finally {
      setIsSubmitting(false);
    }
  }, [form, fetchLectures, handleCancelEdit]);

  const executeUpdate = useCallback(async () => {
    if (!editingLecture) return;
    setConfirmLoading(true);

    try {
      const start_at = toISOStringFromDateAndMinutes(form.date, form.startMinutes);
      const end_at = toISOStringFromDateAndMinutes(form.date, form.endMinutes);

      const res = await fetch(`/api/lectures/${editingLecture.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: form.title,
          discord_name: form.discordName,
          start_at,
          end_at,
          notes: form.notes || null,
        }),
      });

      const body = await res.json();
      setConfirmOpen(false);

      if (!res.ok) {
        setSubmitError(body.error ?? "更新に失敗しました");
        return;
      }

      setSuccessMsg("講座を更新しました ✅");
      await fetchLectures();
      handleCancelEdit();
    } catch {
      setSubmitError("ネットワークエラーが発生しました");
    } finally {
      setConfirmLoading(false);
    }
  }, [editingLecture, form, fetchLectures, handleCancelEdit]);

  const executeDelete = useCallback(async () => {
    if (!confirmTarget) return;
    setConfirmLoading(true);

    try {
      const res = await fetch(`/api/lectures/${confirmTarget.id}`, {
        method: "DELETE",
      });

      const body = await res.json();
      setConfirmOpen(false);

      if (!res.ok) {
        setSubmitError(body.error ?? "削除に失敗しました");
        return;
      }

      setSuccessMsg("講座を削除しました");
      await fetchLectures();
      if (editingLecture?.id === confirmTarget.id) handleCancelEdit();
    } catch {
      setSubmitError("ネットワークエラーが発生しました");
    } finally {
      setConfirmLoading(false);
      setConfirmTarget(null);
    }
  }, [confirmTarget, fetchLectures, editingLecture, handleCancelEdit]);

  const handleConfirmAction = useCallback(() => {
    if (confirmType === "delete") {
      executeDelete();
    } else {
      executeUpdate();
    }
  }, [confirmType, executeDelete, executeUpdate]);

  // ============================================================
  // レンダリング
  // ============================================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-indigo-50/30 to-purple-50/20">
      {/* ページヘッダー */}
      <div className="border-b border-indigo-100 bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs text-indigo-500 font-medium mb-1">
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                2026 Summer Lecture Series
              </div>
              <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
                📅 講座申し込みフォーム
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                8月1日〜9月13日の期間で開催される講座の申し込みができます。
                <span className="ml-1 text-indigo-600 font-medium">同時間帯は先着順（1枠のみ）</span>
              </p>
            </div>

            {/* ログイン状態バッジ */}
            <div className="shrink-0">
              {userInfo ? (
                <div className="flex items-center gap-2 rounded-xl bg-indigo-50 border border-indigo-200 px-4 py-2">
                  <div className="h-2 w-2 rounded-full bg-indigo-500" />
                  <span className="text-sm font-semibold text-indigo-700">
                    @{userInfo.discordName}
                    {userInfo.isAdmin && (
                      <span className="ml-1.5 rounded-full bg-indigo-200 px-2 py-0.5 text-[10px] text-indigo-800 font-bold">
                        Admin
                      </span>
                    )}
                  </span>
                </div>
              ) : (
                <a
                  href="/login"
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
                  </svg>
                  Discordでログイン
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {/* 成功メッセージ */}
        {successMsg && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
            <svg className="h-5 w-5 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-medium">{successMsg}</span>
            <button
              onClick={() => setSuccessMsg(null)}
              className="ml-auto text-green-500 hover:text-green-700"
            >
              ✕
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_380px]">
          {/* 左: カレンダー */}
          <div className="space-y-4">
            {/* 週ナビゲーター */}
            <WeekNavigator
              currentWeekStart={weekStart}
              onPrev={handlePrevWeek}
              onNext={handleNextWeek}
            />

            {/* カレンダー本体 */}
            {isLoadingLectures ? (
              <div className="flex h-96 items-center justify-center rounded-2xl border border-gray-200 bg-white">
                <div className="flex flex-col items-center gap-3 text-gray-400">
                  <svg className="h-8 w-8 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="text-sm">予約情報を読み込み中...</span>
                </div>
              </div>
            ) : (
              <WeeklyCalendar
                weekStart={weekStart}
                lectures={lectures}
                dragSelection={dragSelection}
                userInfo={userInfo}
                onSelectionChange={handleSelectionChange}
                onEditLecture={handleEditLecture}
                onDeleteLecture={handleDeleteRequest}
              />
            )}

            {/* 予約済み一覧（今週分） */}
            {lectures.length > 0 && (
              <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <h3 className="mb-3 text-sm font-bold text-gray-700">
                  📋 全予約一覧（{lectures.length}件）
                </h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {lectures.map((lec) => (
                    <LectureListItem
                      key={lec.id}
                      lecture={lec}
                      userInfo={userInfo}
                      onEdit={handleEditLecture}
                      onDelete={handleDeleteRequest}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 右: フォーム */}
          <div id="booking-form-section">
            <BookingForm
              form={form}
              userInfo={userInfo}
              editingLecture={editingLecture}
              isSubmitting={isSubmitting}
              error={submitError}
              onFormChange={handleFormChange}
              onSubmit={handleSubmit}
              onCancelEdit={handleCancelEdit}
            />
          </div>
        </div>
      </div>

      {/* 確認ダイアログ */}
      <ConfirmModal
        isOpen={confirmOpen}
        type={confirmType}
        lectureTitle={confirmTarget?.title ?? editingLecture?.title ?? ""}
        onConfirm={handleConfirmAction}
        onCancel={() => {
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        isLoading={confirmLoading}
      />
    </div>
  );
}
