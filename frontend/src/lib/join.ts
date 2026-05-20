import { fetchBackend } from "./backendFetch";

/**
 * 入学見込み仮入会フォームが受け付け可能な期間か判定（毎年2月1日～4月5日、日本時間）
 * 
 * @returns true: 受け付け可能期間内、false: 受け付け不可期間
 */
export function isProspectiveFormOpen(): boolean {
  // 日本時間（JST）で現在日付を取得
  // ブラウザの現在時刻から、JST との差分を考慮
  const now = new Date();
  // UTC時刻を取得
  const utcTime = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
  // JSTの時刻を計算（UTC+9）
  const jstTime = new Date(utcTime.getTime() + 9 * 60 * 60 * 1000);
  
  const month = jstTime.getMonth() + 1; // getMonth()は0-11なので+1
  const day = jstTime.getDate();
  
  // 2月1日～4月5日の範囲判定
  if (month === 2 && day >= 1) {
    return true;
  } else if (month === 3) {
    return true;
  } else if (month === 4 && day <= 5) {
    return true;
  } else {
    return false;
  }
}

export type JoinRequestPayload = {
  email: string;
  confirm_email: string;
  name: string;
  form_type: string;
  metadata?: Record<string, unknown> | null;
};

export async function requestOtp(payload: JoinRequestPayload) {
  // 入学見込みフォームの場合、受け付け期間チェックを実施
  if (payload.form_type === "prospective-student" && !isProspectiveFormOpen()) {
    throw new Error("403 入学見込み仮入会は現在受け付けておりません。質問がある場合はお問い合わせフォームよりお問い合わせ下さい。");
  }
  
  const res = await fetchBackend("/api/v1/join/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    // try parse JSON body for structured error (e.g. { detail: "..." })
    let bodyText = await res.text();
    try {
      const json = JSON.parse(bodyText);
      const detail = json.detail ?? json.message ?? JSON.stringify(json);
      throw new Error(`${res.status} ${detail}`);
    } catch (_) {
      throw new Error(`${res.status} ${bodyText}`);
    }
  }
  return res.json();
}

export async function verifyOtp(join_request_id: string, otp_code: string) {
  const res = await fetchBackend("/api/v1/join/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ join_request_id, otp_code }),
  });
  if (!res.ok) {
    let bodyText = await res.text();
    try {
      const json = JSON.parse(bodyText);
      const detail = json.detail ?? json.message ?? JSON.stringify(json);
      throw new Error(`${res.status} ${detail}`);
    } catch (_) {
      throw new Error(`${res.status} ${bodyText}`);
    }
  }
  return res.json();
}
