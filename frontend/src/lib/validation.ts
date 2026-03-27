export function validateFullName(name: string): boolean {
  if (!name || typeof name !== "string") return false;
  const v = name.trim();
  // Require at least one half-width space between family and given name. Allow additional name parts.
  // Example valid: "山田 太郎", "Smith John Paul"
  const re = /^\S+ \S+(?: \S+)*$/u;
  return re.test(v);
}

export default validateFullName;

/**
 * All available departments (for select dropdown, etc.)
 */
export const ALL_DEPARTMENTS = [
  // Aoyama campus (17 departments)
  "文学部 英米文学科",
  "文学部 フランス文学科",
  "文学部 日本文学科",
  "文学部 史学科",
  "文学部 比較芸術学科",
  "経済学部 経済学科",
  "経済学部 現代経済デザイン学科",
  "法学部 法学科",
  "法学部 ヒューマンライツ学科",
  "経営学部 経営学科",
  "経営学部 マーケティング学科",
  "国際政治経済学部 国際政治学科",
  "国際政治経済学部 国際経済学科",
  "国際政治経済学部 国際コミュニケーション学科",
  "総合文化政策学部 総合文化政策学科",
  "教育人間科学部 教育学科",
  "教育人間科学部 心理学科",
  // Sagamihara campus (10 departments)
  "理工学部 物理化学科",
  "理工学部 数理サイエンス学科",
  "理工学部 化学・生命科学科",
  "理工学部 電気電子工学科",
  "理工学部 機械創造工学科",
  "理工学部 経営システム工学科",
  "理工学部 情報テクノロジー学科",
  "社会情報学部 社会情報学科",
  "地球社会共生学部 地球社会共生学科",
  "コミュニティ人間科学部 コミュニティ人間科学科",
];

/**
 * Student ID code → available departments mapping
 */
const DEPARTMENTS_FOR_CODE = {
  // Aoyama campus
  "113": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "114": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "115": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "116": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "117": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "118": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "119": ["文学部 英米文学科", "文学部 フランス文学科", "文学部 日本文学科", "文学部 史学科", "文学部 比較芸術学科"],
  "121": ["経済学部 経済学科", "経済学部 現代経済デザイン学科"],
  "122": ["経済学部 経済学科", "経済学部 現代経済デザイン学科"],
  "131": ["法学部 法学科", "法学部 ヒューマンライツ学科"],
  "132": ["法学部 法学科", "法学部 ヒューマンライツ学科"],
  "141": ["経営学部 経営学科", "経営学部 マーケティング学科"],
  "142": ["経営学部 経営学科", "経営学部 マーケティング学科"],
  "161": ["国際政治経済学部 国際政治学科", "国際政治経済学部 国際経済学科", "国際政治経済学部 国際コミュニケーション学科"],
  "162": ["国際政治経済学部 国際政治学科", "国際政治経済学部 国際経済学科", "国際政治経済学部 国際コミュニケーション学科"],
  "163": ["国際政治経済学部 国際政治学科", "国際政治経済学部 国際経済学科", "国際政治経済学部 国際コミュニケーション学科"],
  "164": ["国際政治経済学部 国際政治学科", "国際政治経済学部 国際経済学科", "国際政治経済学部 国際コミュニケーション学科"],
  "171": ["総合文化政策学部 総合文化政策学科"],
  "191": ["教育人間科学部 教育学科", "教育人間科学部 心理学科"],
  "192": ["教育人間科学部 教育学科", "教育人間科学部 心理学科"],
  // Sagamihara campus
  "151": ["理工学部 物理化学科", "理工学部 数理サイエンス学科", "理工学部 化学・生命科学科", "理工学部 電気電子工学科", "理工学部 機械創造工学科", "理工学部 経営システム工学科", "理工学部 情報テクノロジー学科"],
  "152": ["理工学部 物理化学科", "理工学部 数理サイエンス学科", "理工学部 化学・生命科学科", "理工学部 電気電子工学科", "理工学部 機械創造工学科", "理工学部 経営システム工学科", "理工学部 情報テクノロジー学科"],
  "153": ["理工学部 物理化学科", "理工学部 数理サイエンス学科", "理工学部 化学・生命科学科", "理工学部 電気電子工学科", "理工学部 機械創造工学科", "理工学部 経営システム工学科", "理工学部 情報テクノロジー学科"],
  "154": ["理工学部 電気電子工学科"],
  "155": ["理工学部 物理化学科", "理工学部 数理サイエンス学科", "理工学部 化学・生命科学科", "理工学部 電気電子工学科", "理工学部 機械創造工学科", "理工学部 経営システム工学科", "理工学部 情報テクノロジー学科"],
  "156": ["理工学部 機械創造工学科"],
  "157": ["理工学部 経営システム工学科"],
  "158": ["理工学部 情報テクノロジー学科"],
  "159": ["理工学部 物理化学科"],
  "15A": ["理工学部 物理化学科", "理工学部 数理サイエンス学科", "理工学部 化学・生命科学科", "理工学部 電気電子工学科", "理工学部 機械創造工学科", "理工学部 経営システム工学科", "理工学部 情報テクノロジー学科"],
  "181": ["社会情報学部 社会情報学科"],
  "1A1": ["地球社会共生学部 地球社会共生学科"],
  "1B1": ["コミュニティ人間科学部 コミュニティ人間科学科"],
};

/**
 * Extract departments from student ID based on code.
 * Supports multiple formats:
 * - Full format: A + 7 digits (e.g., "A1812345")
 * - Numeric only: 7 digits (e.g., "1812345")
 * - Code only: 3 digits (e.g., "181")
 * @param studentId - The student ID
 * @returns Array of available department names or null if code not mapped
 */
export function getDepartmentsFromStudentId(studentId: string): string[] | null {
  if (!studentId) return null;

  // Normalize: remove leading 'A' if present, uppercase and trim
  const normalized = studentId.toUpperCase().replace(/^A/, "").trim();
  if (normalized.length === 0) return null;

  // Use prefix matching: take up to first 3 characters but allow shorter prefixes
  const prefix = normalized.slice(0, Math.min(3, normalized.length));

  // Collect departments for all codes that start with the prefix (forward match)
  const matches: string[] = [];
  for (const key of Object.keys(DEPARTMENTS_FOR_CODE)) {
    if (key.startsWith(prefix)) {
      const list = DEPARTMENTS_FOR_CODE[key as keyof typeof DEPARTMENTS_FOR_CODE];
      if (Array.isArray(list)) matches.push(...list);
    }
  }

  if (matches.length === 0) return null;

  // Deduplicate while preserving order
  const deduped: string[] = [];
  const seen = new Set<string>();
  for (const d of matches) {
    if (!seen.has(d)) {
      seen.add(d);
      deduped.push(d);
    }
  }

  return deduped;
}
