"use client";

import React, { useState, useEffect, useRef } from "react";
import OTPInput from "@/components/OTPInput";
import { requestOtp, verifyOtp } from "@/lib/join";
import { LoaderCircle } from "lucide-react";
import { btnPrimary, btnSecondary } from "./joinStyles";

const infoText = "my-2 text-sm text-slate-700";
const spinner = "mr-2 inline size-4 animate-spin align-middle text-slate-500";

type Props = {
  email: string;
  name: string;
  formType: string;
  onClose?: () => void;
  autoSend?: boolean;
};

export default function OTPModal({ email, name, formType, onClose, autoSend }: Props) {
  const [joinId, setJoinId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [resendSeconds, setResendSeconds] = useState<number>(0);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const autoSendRef = useRef(false);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const isBusy = status === "sending" || status === "verifying";

  async function sendOtp() {
    setError(null);
    setStatus("sending");
    try {
      const res = await requestOtp({ email, confirm_email: email, name, form_type: formType });
      setJoinId(res.id);
      setStatus("sent");
      // start resend cooldown
      setResendSeconds(30);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus(null);
    }
  }

  useEffect(() => {
    if (autoSend && status === null && !autoSendRef.current) {
      autoSendRef.current = true;
      void sendOtp();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleComplete(code: string) {
    if (!joinId) return setError("No join id");
    setError(null);
    setStatus("verifying");
    try {
      const res = await verifyOtp(joinId, code);
      setInviteUrl(res.discord_invite_url ?? null);
      setStatus("verified");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("sent");
    }
  }

  // countdown for resend button
  useEffect(() => {
    if (resendSeconds <= 0) return;
    const t = setInterval(() => setResendSeconds((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [resendSeconds]);

  // focus modal and handle Esc to close
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    modalRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose?.();
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus();
    };
  }, [onClose]);

  // copy feedback
  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus("コピーしました");
      setTimeout(() => setCopyStatus(null), 2000);
    } catch {
      setCopyStatus("コピーに失敗しました");
      setTimeout(() => setCopyStatus(null), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl focus:outline-none" ref={modalRef} tabIndex={-1} aria-label="メール認証ダイアログ">
        <div className="mb-2">
          <h3 className="m-0 mb-1 text-lg font-semibold text-slate-900">メール認証コードの送信</h3>
          <p className="m-0 text-sm text-slate-500">送信先: {email}</p>
        </div>

        <div className="mt-2">
          {status === null && (
            <div className="flex gap-2">
              <button type="button" onClick={sendOtp} className={btnPrimary} disabled={isBusy}>送信</button>
              <button type="button" onClick={onClose} className={btnSecondary}>キャンセル</button>
            </div>
          )}

          {status === "sending" && <p className={infoText}><LoaderCircle className={spinner} aria-hidden="true" /> 送信中…</p>}

          {status === "sent" && (
            <div>
              <p className={infoText}>認証コードを送信しました。メールに届いた6桁のコードを入力してください。</p>
              <OTPInput onComplete={handleComplete} />
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={sendOtp} className={btnSecondary} disabled={resendSeconds > 0 || isBusy}>
                  {resendSeconds > 0 ? `再送 (${resendSeconds}s)` : "再送"}
                </button>
                <button type="button" onClick={onClose} className={btnSecondary}>閉じる</button>
              </div>
            </div>
          )}

          {status === "verifying" && <p className={infoText}><LoaderCircle className={spinner} aria-hidden="true" /> 確認中…</p>}

          {status === "verified" && (
            <div>
              <p className="my-1 font-bold text-emerald-700">認証に成功しました。</p>
              {inviteUrl ? (
                <div className="mt-2 flex items-center gap-2">
                  <p className="m-0 max-w-90 truncate text-sm text-slate-900">Discord招待: <a href={inviteUrl} target="_blank" rel="noreferrer" className="text-blue-700 underline">{inviteUrl}</a></p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void handleCopy(inviteUrl)}
                      className="inline-flex h-8 items-center justify-center rounded-md border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                    >コピー</button>
                    {copyStatus ? <span className="text-sm text-slate-700">{copyStatus}</span> : null}
                  </div>
                </div>
              ) : (
                <p className={infoText}>招待リンクはまもなく届きます。</p>
              )}
              <div className="mt-3">
                <button type="button" onClick={onClose} className={btnSecondary}>閉じる</button>
              </div>
            </div>
          )}

          {error && <p className="mt-2 text-sm font-semibold text-red-700">エラー: {error}</p>}
        </div>
      </div>
    </div>
  );
}
