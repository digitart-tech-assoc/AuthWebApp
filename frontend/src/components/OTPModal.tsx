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
  const autoSendRef = useRef(false);

  async function sendOtp() {
    setError(null);
    setStatus("sending");
    try {
      const res = await requestOtp({ email, confirm_email: email, name, form_type: formType });
      setJoinId(res.id);
      setStatus("sent");
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

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true">
      <div className={styles.modal}>
        <div className={styles.header}>
          <h3 className={styles.title}>メール認証コードの送信</h3>
          <p className={styles.subtitle}>送信先: {email}</p>
        </div>

        <div className={styles.body}>
          {status === null && (
            <div className={styles.row}>
              <button onClick={sendOtp} className={`${styles.button} ${styles.primary}`}>送信</button>
              <button onClick={onClose} className={styles.button}>キャンセル</button>
            </div>
          )}

          {status === "sending" && <p className={styles.info}>送信中…</p>}

          {status === "sent" && (
            <div>
              <p className={styles.info}>認証コードを送信しました。メールに届いた6桁のコードを入力してください。</p>
              <OTPInput onComplete={handleComplete} />
              <div className={styles.row} style={{ marginTop: 12 }}>
                <button onClick={sendOtp} className={styles.button}>再送</button>
                <button onClick={onClose} className={styles.button}>閉じる</button>
              </div>
            </div>
          )}

          {status === "verifying" && <p className={styles.info}>確認中…</p>}

          {status === "verified" && (
            <div>
              <p className={styles.success}>認証に成功しました。</p>
              {inviteUrl ? (
                <div className={styles.inviteRow}>
                  <p className={styles.inviteText}>Discord招待: <a href={inviteUrl} target="_blank" rel="noreferrer" className={styles.inviteLink}>{inviteUrl}</a></p>
                  <button
                    onClick={() => void navigator.clipboard.writeText(inviteUrl)}
                    className={`${styles.button} ${styles.copyButton}`}
                  >コピー</button>
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
