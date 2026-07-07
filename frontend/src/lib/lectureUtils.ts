import { Lecture, SLOT_MINUTES, CALENDAR_START_HOUR, CALENDAR_END_HOUR } from "./lectureTypes";

// ============================================================
// 日時ユーティリティ
// ============================================================

/** 分数 → "HH:MM" 形式 */
export function minutesToTimeString(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/** "HH:MM" → 分数 */
export function timeStringToMinutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

/** Date → "YYYY-MM-DD" (JST) */
export function toDateString(date: Date): string {
  const jst = new Date(date.getTime() + 9 * 60 * 60 * 1000);
  return jst.toISOString().slice(0, 10);
}

/** "YYYY-MM-DD" + 分数 → ISO 8601 文字列 (JST) */
export function toISOStringFromDateAndMinutes(dateStr: string, minutes: number): string {
  const [y, mo, d] = dateStr.split("-").map(Number);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  // JST(+09:00)の日時を ISO で表現
  const dt = new Date(Date.UTC(y, mo - 1, d, h - 9, m));
  return dt.toISOString();
}

/** ISO 8601 → "YYYY-MM-DD" (JST) */
export function isoToDateString(iso: string): string {
  const date = new Date(iso);
  return toDateString(date);
}

/** ISO 8601 → その日の 00:00 からの分数 (JST) */
export function isoToMinutes(iso: string): number {
  const date = new Date(iso);
  const jst = new Date(date.getTime() + 9 * 60 * 60 * 1000);
  return jst.getUTCHours() * 60 + jst.getUTCMinutes();
}

/** 分数を20分単位にスナップ（切り捨て） */
export function snapToSlot(minutes: number): number {
  return Math.floor(minutes / SLOT_MINUTES) * SLOT_MINUTES;
}

/** カレンダー内のピクセル Y座標 → 分数（カレンダー開始時刻からの offset） */
export function pixelToMinutes(
  y: number,
  containerHeight: number
): number {
  const totalMinutes = (CALENDAR_END_HOUR - CALENDAR_START_HOUR) * 60;
  const raw = (y / containerHeight) * totalMinutes + CALENDAR_START_HOUR * 60;
  return snapToSlot(Math.max(CALENDAR_START_HOUR * 60, Math.min(CALENDAR_END_HOUR * 60, raw)));
}

/** 分数 → カレンダー内の割合 (0〜1) */
export function minutesToPercent(minutes: number): number {
  const totalMinutes = (CALENDAR_END_HOUR - CALENDAR_START_HOUR) * 60;
  return (minutes - CALENDAR_START_HOUR * 60) / totalMinutes;
}

/** カレンダーの時間目盛り（整数時間のみ）を生成 */
export function generateHourSlots(): number[] {
  const slots: number[] = [];
  for (let h = CALENDAR_START_HOUR; h <= CALENDAR_END_HOUR; h++) {
    slots.push(h * 60);
  }
  return slots;
}

/** 20分単位のセレクトボックス用オプションを生成 */
export function generateTimeOptions(): { value: number; label: string }[] {
  const options: { value: number; label: string }[] = [];
  for (let h = CALENDAR_START_HOUR; h <= CALENDAR_END_HOUR; h++) {
    for (let m = 0; m < 60; m += SLOT_MINUTES) {
      if (h === CALENDAR_END_HOUR && m > 0) break;
      const minutes = h * 60 + m;
      options.push({ value: minutes, label: minutesToTimeString(minutes) });
    }
  }
  return options;
}

// ============================================================
// 週ナビゲーション
// ============================================================

/** ある日付を含む週の月曜日を返す */
export function getWeekStart(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun, 1=Mon...
  const diff = (day === 0 ? -6 : 1 - day); // 月曜起点
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** weekStart から7日分の日付配列を生成 */
export function getWeekDays(weekStart: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });
}

/** 日本語曜日略称 */
export const DAY_NAMES_JA = ["月", "火", "水", "木", "金", "土", "日"];

/** Date → "M/D (曜)" 形式 */
export function formatDateHeader(date: Date): string {
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const dow = DAY_NAMES_JA[date.getDay() === 0 ? 6 : date.getDay() - 1];
  return `${m}/${d} (${dow})`;
}

/** Date → "M/D" 形式 */
export function formatDateShort(date: Date): string {
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

// ============================================================
// 重複チェック
// ============================================================

/** 既存講座リストと選択時間帯が重複するかチェック */
export function hasOverlap(
  lectures: Lecture[],
  dateStr: string,
  startMins: number,
  endMins: number,
  excludeId?: string
): boolean {
  return lectures.some((lec) => {
    if (excludeId && lec.id === excludeId) return false;
    if (isoToDateString(lec.start_at) !== dateStr) return false;
    const ls = isoToMinutes(lec.start_at);
    const le = isoToMinutes(lec.end_at);
    // 半開区間 [start, end) での重複判定
    return startMins < le && endMins > ls;
  });
}

/** ある日付の講座リストを取得 */
export function getLecturesForDate(lectures: Lecture[], dateStr: string): Lecture[] {
  return lectures.filter((lec) => isoToDateString(lec.start_at) === dateStr);
}

// ============================================================
// 表示フォーマット
// ============================================================

/** "HH:MM - HH:MM" 形式の時間表示 */
export function formatTimeRange(startIso: string, endIso: string): string {
  return `${minutesToTimeString(isoToMinutes(startIso))} - ${minutesToTimeString(isoToMinutes(endIso))}`;
}
