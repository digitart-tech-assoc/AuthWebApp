// 講座データの型定義

export interface Lecture {
  id: string;
  title: string;
  start_at: string; // ISO 8601
  end_at: string;   // ISO 8601
  discord_name: string;
  notes: string | null;
  is_authenticated_booking: boolean;
  user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface LectureInsert {
  title: string;
  start_at: string;
  end_at: string;
  discord_name: string;
  notes?: string | null;
  is_authenticated_booking: boolean;
  user_id?: string | null;
}

export interface LectureUpdate {
  title?: string;
  start_at?: string;
  end_at?: string;
  discord_name?: string;
  notes?: string;
}

/** ドラッグ選択中の一時状態 */
export interface DragSelection {
  date: string;        // "YYYY-MM-DD"
  startMinutes: number; // 00:00 からの分数
  endMinutes: number;
}

/** フォームの状態 */
export interface FormState {
  title: string;
  discordName: string;
  date: string;         // "YYYY-MM-DD"
  startMinutes: number; // 00:00 からの分数
  endMinutes: number;
  notes: string;
}

/** ユーザー情報 */
export interface UserInfo {
  id: string;
  discordName: string | null;
  discordId: string | null;
  isAdmin: boolean;
}

/** 操作モード */
export type FormMode = "create" | "edit";

/** 確認ダイアログの種別 */
export type ConfirmType = "update" | "delete";

// 申込期間定数
export const BOOKING_START = new Date("2026-08-01T00:00:00+09:00");
export const BOOKING_END   = new Date("2026-09-13T23:59:59+09:00");

// カレンダー表示時間
export const CALENDAR_START_HOUR = 0;
export const CALENDAR_END_HOUR   = 24;
export const SLOT_MINUTES        = 20; // 20分単位スナップ
