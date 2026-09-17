// 入会・アンケート・学生プロファイル関連の共通型定義

export interface SurveyAnswers {
  digitart_channels: string[];
  digitart_channels_other: string;
  circle_search_channels: string[];
  circle_search_other: string;
  discord_invite_other: string;
  discord_invite_source: string | null;
  interested_fields: string[];
  interested_fields_other: string;
  motivations: string[];
  motivations_other: string;
}

export interface StudentProfile {
  student_number: string;
  name: string;
  furigana: string;
  department: string;
  gender: string | null;
  phone: string;
  email_aoyama: string;
}

export interface EligibilityCheckResult {
  is_discord_linked: boolean;
  is_pre_member: boolean;
  is_paid: boolean;
  can_register: boolean;
  reason: string;
}
