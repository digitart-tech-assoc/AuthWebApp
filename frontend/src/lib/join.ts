import { fetchBackend } from "./backendFetch";

export type JoinRequestPayload = {
  email: string;
  confirm_email: string;
  name: string;
  form_type: string;
  metadata?: Record<string, unknown> | null;
};

export async function requestOtp(payload: JoinRequestPayload) {
  const res = await fetchBackend("/api/v1/join/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`requestOtp failed: ${res.status} ${err}`);
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
    const err = await res.text();
    throw new Error(`verifyOtp failed: ${res.status} ${err}`);
  }
  return res.json();
}
