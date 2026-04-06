"use client";

import React, { useState, useEffect, useRef } from "react";
import OTPInput from "./OTPInput";
import { requestOtp, verifyOtp } from "../lib/join";
import styles from "./OTPModal.module.css";

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
    } catch (e: any) {
      setError(e?.message ?? String(e));
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
    } catch (e: any) {
      setError(e?.message ?? String(e));
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
    } catch (_) {
      setCopyStatus("コピーに失敗しました");
      setTimeout(() => setCopyStatus(null), 2000);
    }
  };

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true">
      <div className={styles.modal} ref={modalRef} tabIndex={-1} aria-label="メール認証ダイアログ">
        <div className={styles.header}>
          <h3 className={styles.title}>メール認証コードの送信</h3>
          <p className={styles.subtitle}>送信先: {email}</p>
        </div>

        <div className={styles.body}>
          {status === null && (
            <div className={styles.row}>
              <button onClick={sendOtp} className={`${styles.button} ${styles.primary}`} disabled={isBusy}>送信</button>
              <button onClick={onClose} className={styles.button}>キャンセル</button>
            </div>
          )}

          {status === "sending" && <p className={styles.info}><span className={styles.spinner} aria-hidden></span> 送信中…</p>}

          {status === "sent" && (
            <div>
              <p className={styles.info}>認証コードを送信しました。メールに届いた6桁のコードを入力してください。</p>
              <OTPInput onComplete={handleComplete} />
              <div className={styles.row} style={{ marginTop: 12 }}>
                <button onClick={sendOtp} className={styles.button} disabled={resendSeconds > 0 || isBusy}>
                  {resendSeconds > 0 ? `再送 (${resendSeconds}s)` : "再送"}
                </button>
                <button onClick={onClose} className={styles.button}>閉じる</button>
              </div>
            </div>
          )}

          {status === "verifying" && <p className={styles.info}><span className={styles.spinner} aria-hidden></span> 確認中…</p>}

          {status === "verified" && (
            <div>
              <p className={styles.success}>認証に成功しました。</p>
              {inviteUrl ? (
                <div className={styles.inviteRow}>
                  <p className={styles.inviteText}>Discord招待: <a href={inviteUrl} target="_blank" rel="noreferrer" className={styles.inviteLink}>{inviteUrl}</a></p>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button
                      onClick={() => void handleCopy(inviteUrl)}
                      className={`${styles.button} ${styles.copyButton}`}
                    >コピー</button>
                    {copyStatus ? <span style={{ fontSize: 13, color: '#374151' }}>{copyStatus}</span> : null}
                  </div>
                </div>
              ) : (
                <p className={styles.info}>招待リンクはまもなく届きます。</p>
              )}
              <div style={{ marginTop: 12 }}>
                <button onClick={onClose} className={styles.button}>閉じる</button>
              </div>
            </div>
          )}

          {error && <p className={styles.error}>エラー: {error}</p>}
        </div>
      </div>
    </div>
  );
}
