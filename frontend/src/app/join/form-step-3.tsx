"use client";

import { useState, useEffect } from "react";
import { sendOTP, verifyOTP, submitStudentProfile } from "@/actions/student-registration";
import OTPInput from "@/components/OTPInput";
import styles from "./join.module.css";

interface FormData {
  student_number: string;
  name: string;
  furigana: string;
  department: string;
  gender: string | null;
  phone: string;
}

interface FormStep3Props {
  studentNumber: string;
  name: string;
  onComplete: () => void;
  onBack: () => void;
  formData: FormData;
}

export default function FormStep3OTP({
  studentNumber,
  name,
  onComplete,
  onBack,
  formData,
}: FormStep3Props) {
  const [emailAoyama, setEmailAoyama] = useState<string | null>(null);
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendCountdown, setResendCountdown] = useState(0);
  const [expiresIn, setExpiresIn] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (resendCountdown > 0) {
      const timer = setTimeout(() => setResendCountdown(resendCountdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCountdown]);

  const handleSendOTP = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await sendOTP(studentNumber, name);
      setEmailAoyama(result.email_aoyama);
      setOtpSent(true);
      setResendCountdown(60);
      setExpiresIn(result.expires_in_seconds);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OTP 送信に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    try {
      setSubmitting(true);
      setError(null);

      // OTP verification
      await verifyOTP(otpCode);

      // Submit profile
      await submitStudentProfile(formData);

      // Complete
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "認証に失敗しました");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>メール認証（OTP）</h2>

      <div style={{ marginTop: "16px" }}>
        {!otpSent ? (
          <div>
            <p style={{ marginBottom: "16px", color: "#64748b" }}>
              登録した青山学院大学のメールアドレスに確認コードを送信します。
            </p>

            <button
              onClick={handleSendOTP}
              disabled={loading}
              style={{
                padding: "12px 24px",
                background: loading ? "#cbd5e1" : "#3b82f6",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: "16px",
                fontWeight: "600",
              }}
            >
              {loading ? "送信中..." : "確認コードを送信"}
            </button>
          </div>
        ) : (
          <div>
            <p style={{ marginBottom: "8px", fontWeight: "600" }}>
              確認コードを {emailAoyama} に送信しました
            </p>
            <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "16px" }}>
              有効期限: {expiresIn ? `${Math.floor(expiresIn / 60)} 分` : "10 分"}
            </p>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", marginBottom: "8px", fontWeight: "600" }}>
                確認コード (6桁)
              </label>
              <OTPInput
                value={otpCode}
                onChange={setOtpCode}
                disabled={submitting}
              />
            </div>

            <div style={{ display: "flex", gap: "12px", justifyContent: "space-between" }}>
              <button
                onClick={() => {
                  setOtpCode("");
                  setOtpSent(false);
                }}
                disabled={submitting || resendCountdown > 0}
                style={{
                  padding: "12px 24px",
                  background: submitting || resendCountdown > 0 ? "#cbd5e1" : "#e5e7eb",
                  color: "#1f2937",
                  border: "none",
                  borderRadius: "6px",
                  cursor: submitting || resendCountdown > 0 ? "not-allowed" : "pointer",
                  fontSize: "14px",
                  fontWeight: "600",
                }}
              >
                {resendCountdown > 0 ? `再送信 (${resendCountdown}s)` : "コードを再送信"}
              </button>

              <button
                onClick={handleVerifyOTP}
                disabled={submitting || otpCode.length !== 6}
                style={{
                  padding: "12px 24px",
                  background: submitting || otpCode.length !== 6 ? "#cbd5e1" : "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: submitting || otpCode.length !== 6 ? "not-allowed" : "pointer",
                  fontSize: "16px",
                  fontWeight: "600",
                }}
              >
                {submitting ? "検証中..." : "認証 →"}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              marginTop: "16px",
              padding: "12px",
              background: "#fee2e2",
              color: "#dc2626",
              borderRadius: "6px",
              fontSize: "14px",
            }}
          >
            {error}
          </div>
        )}
      </div>

      <div style={{ marginTop: "24px", borderTop: "1px solid #e5e7eb", paddingTop: "16px" }}>
        <button
          onClick={onBack}
          disabled={submitting}
          style={{
            padding: "12px 24px",
            background: submitting ? "#cbd5e1" : "#e5e7eb",
            color: "#1f2937",
            border: "none",
            borderRadius: "6px",
            cursor: submitting ? "not-allowed" : "pointer",
            fontSize: "16px",
            fontWeight: "600",
          }}
        >
          ← 戻る
        </button>
      </div>
    </div>
  );
}
