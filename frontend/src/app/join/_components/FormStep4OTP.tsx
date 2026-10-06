"use client";

import { useState, useEffect } from "react";
import { sendOTP, verifyOTP, submitStudentProfile } from "@/actions/studentRegistration";
import OTPInput from "@/components/OTPInput";
import { alertError, btnPrimary, btnSecondary, card, cardTitle, fieldLabel } from "./joinStyles";
import type { StudentProfileInput } from "@/types/join";

interface FormStep4Props {
  studentNumber: string;
  name: string;
  onComplete: () => void;
  onBack: () => void;
  formData: StudentProfileInput;
}

export default function FormStep4OTP({
  studentNumber,
  name,
  onComplete,
  onBack,
  formData,
}: FormStep4Props) {
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

      // Submit profile (include email_aoyama for type completeness)
      await submitStudentProfile({ ...formData, email_aoyama: emailAoyama ?? "" });

      // Complete
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "認証に失敗しました");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={card}>
      <h2 className={cardTitle}>メール認証（OTP）</h2>

      <div className="mt-4">
        {!otpSent ? (
          <div>
            <p className="mb-4 text-sm leading-relaxed text-slate-500">
              登録した青山学院大学のメールアドレスに確認コードを送信します。
            </p>

            <button type="button" onClick={handleSendOTP} disabled={loading} className={btnPrimary}>
              {loading ? "送信中..." : "確認コードを送信"}
            </button>
          </div>
        ) : (
          <div>
            <p className="mb-2 text-sm font-semibold text-slate-900">
              確認コードを {emailAoyama} に送信しました
            </p>
            <p className="mb-4 text-xs text-slate-500">
              有効期限: {expiresIn ? `${Math.floor(expiresIn / 60)} 分` : "10 分"}
            </p>

            <div className="mb-4">
              <label className={fieldLabel}>
                確認コード (6桁)
              </label>
              <OTPInput
                value={otpCode}
                onChange={setOtpCode}
                disabled={submitting}
              />
            </div>

            <div className="flex justify-between gap-3">
              <button
                type="button"
                onClick={() => {
                  setOtpCode("");
                  setOtpSent(false);
                }}
                disabled={submitting || resendCountdown > 0}
                className={btnSecondary}
              >
                {resendCountdown > 0 ? `再送信 (${resendCountdown}s)` : "コードを再送信"}
              </button>

              <button
                type="button"
                onClick={handleVerifyOTP}
                disabled={submitting || otpCode.length !== 6}
                className={btnPrimary}
              >
                {submitting ? "検証中..." : "認証 →"}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className={`${alertError} mt-4`}>
            {error}
          </div>
        )}
      </div>

      <div className="mt-6 border-t border-slate-200 pt-4">
        <button type="button" onClick={onBack} disabled={submitting} className={btnSecondary}>
          ← 戻る
        </button>
      </div>
    </div>
  );
}
