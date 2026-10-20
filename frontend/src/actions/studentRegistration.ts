"use server";

import { backendFetch } from "@/lib/backendFetch";
import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { type ActionResult, type StatusMessages, messageForStatus } from "@/lib/errorMessages";
import { getForwardedForHeader } from "@/lib/forwardedHeaders";

import type { EligibilityCheckResult, StudentProfile } from "@/types/join";

export async function checkEligibility(): Promise<EligibilityCheckResult> {
  const headerResult = await getBackendAuthorizationHeader();
  if (!headerResult) {
    throw new Error("Not authenticated");
  }

  try {
    const response = await backendFetch("/api/v1/student/validate-eligibility", {
      method: "POST",
      headers: {
        "Authorization": headerResult,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to check eligibility: ${response.statusText}`);
    }

    return response.json();
  } catch {
    // If backend is unreachable, return a safe failure so the UI can render an informative message
    return {
      is_discord_linked: false,
      is_pre_member: false,
      is_paid: false,
      can_register: false,
      reason: "バックエンドに接続できません。管理者に連絡してください。",
    } as EligibilityCheckResult;
  }
}

export async function getStudentProfile(): Promise<StudentProfile | null> {
  const headerResult = await getBackendAuthorizationHeader();
  if (!headerResult) {
    return null;
  }

  try {
    const response = await backendFetch("/api/v1/student/profile", {
      method: "GET",
      headers: {
        "Authorization": headerResult,
      },
    });

    if (!response.ok) {
      return null;
    }

    return response.json();
  } catch {
    return null;
  }
}

// Backend のエラー文言は返さず、HTTP ステータスに応じた固定文言を返す（詳細は Backend のログで確認する）
const NOT_AUTHENTICATED_MESSAGE = "ログインの有効期限が切れました。再度ログインしてください。";
const NOT_ELIGIBLE_MESSAGE = "入会資格を確認できませんでした。仮入会の登録と入会費の支払いが完了しているか確認してください。";

const SEND_OTP_ERROR_MESSAGES: StatusMessages = {
  401: NOT_AUTHENTICATED_MESSAGE,
  403: NOT_ELIGIBLE_MESSAGE,
  422: "入力内容を確認してください。",
  429: "送信回数の上限に達しました。しばらく時間をおいてから再度お試しください。",
  default: "認証コードの送信に失敗しました。時間をおいて再度お試しください。",
};

const VERIFY_OTP_ERROR_MESSAGES: StatusMessages = {
  400: "認証コードが正しくないか、有効期限が切れています。",
  401: NOT_AUTHENTICATED_MESSAGE,
  403: NOT_ELIGIBLE_MESSAGE,
  409: "認証コードの確認が同時に行われています。しばらく待ってから再度お試しください。",
  429: "入力回数の上限に達しました。認証コードを再送信してください。",
  default: "認証に失敗しました。時間をおいて再度お試しください。",
};

const SUBMIT_PROFILE_ERROR_MESSAGES: StatusMessages = {
  400: "メール認証が完了していません。認証コードを入力してください。",
  401: NOT_AUTHENTICATED_MESSAGE,
  403: NOT_ELIGIBLE_MESSAGE,
  422: "入力内容を確認してください。",
  default: "プロフィールの保存に失敗しました。時間をおいて再度お試しください。",
};

async function postToBackend<T>(
  path: string,
  body: unknown,
  messages: StatusMessages,
): Promise<ActionResult<T>> {
  const headerResult = await getBackendAuthorizationHeader();
  if (!headerResult) {
    return { ok: false, error: NOT_AUTHENTICATED_MESSAGE };
  }

  try {
    const response = await backendFetch(path, {
      method: "POST",
      headers: {
        ...(await getForwardedForHeader()),
        "Authorization": headerResult,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return { ok: false, error: messageForStatus(response.status, messages) };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch {
    return { ok: false, error: messages.default };
  }
}

export async function sendOTP(
  studentNumber: string,
  name: string
): Promise<ActionResult<{ email_aoyama: string; expires_in_seconds: number }>> {
  return postToBackend(
    "/api/v1/student/otp/send",
    { student_number: studentNumber, name },
    SEND_OTP_ERROR_MESSAGES,
  );
}

export async function verifyOTP(code: string): Promise<ActionResult<{ verified: boolean }>> {
  return postToBackend("/api/v1/student/otp/verify", { code }, VERIFY_OTP_ERROR_MESSAGES);
}

export async function submitStudentProfile(
  data: StudentProfile
): Promise<ActionResult<{ profile_id: string; message: string }>> {
  return postToBackend(
    "/api/v1/student/profile",
    {
      student_number: data.student_number,
      name: data.name,
      furigana: data.furigana,
      department: data.department,
      gender: data.gender || null,
      phone: data.phone,
    },
    SUBMIT_PROFILE_ERROR_MESSAGES,
  );
}
