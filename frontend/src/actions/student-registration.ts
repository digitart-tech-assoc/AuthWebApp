"use server";

import { backendFetch, getBackendAuthorizationHeader } from "@/lib/backendFetch";

export interface EligibilityCheckResult {
  is_discord_linked: boolean;
  is_pre_member: boolean;
  is_paid: boolean;
  can_register: boolean;
  reason: string;
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
  } catch (err) {
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

export async function sendOTP(
  studentNumber: string,
  name: string
): Promise<{ email_aoyama: string; expires_in_seconds: number }> {
  const headerResult = await getBackendAuthorizationHeader();
  if (!headerResult) {
    throw new Error("Not authenticated");
  }

  const response = await backendFetch("/api/v1/student/otp/send", {
    method: "POST",
    headers: {
      "Authorization": headerResult,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      student_number: studentNumber,
      name: name,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to send OTP: ${response.statusText}`);
  }

  return response.json();
}

export async function verifyOTP(code: string): Promise<{ verified: boolean }> {
  const headerResult = await getBackendAuthorizationHeader();
  if (!headerResult) {
    throw new Error("Not authenticated");
  }

  const response = await backendFetch("/api/v1/student/otp/verify", {
    method: "POST",
    headers: {
      "Authorization": headerResult,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code: code,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to verify OTP: ${response.statusText}`);
  }

  return response.json();
}

export async function submitStudentProfile(
  data: StudentProfile
): Promise<{ profile_id: string; message: string }> {
  const headerResult = await getBackendAuthorizationHeader();
  if (!headerResult) {
    throw new Error("Not authenticated");
  }

  const response = await backendFetch("/api/v1/student/profile", {
    method: "POST",
    headers: {
      "Authorization": headerResult,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      student_number: data.student_number,
      name: data.name,
      furigana: data.furigana,
      department: data.department,
      gender: data.gender || null,
      phone: data.phone,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to submit profile: ${response.statusText}`);
  }

  return response.json();
}
