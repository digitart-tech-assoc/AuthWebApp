"use client";

import React, { useState } from "react";
import OTPInput from "./OTPInput";
import { requestOtp, verifyOtp } from "../lib/join";

type Props = {
  email: string;
  name: string;
  formType: string;
  onClose?: () => void;
};

export default function OTPModal({ email, name, formType, onClose }: Props) {
  const [joinId, setJoinId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);

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
    <div style={{ position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(2,6,23,0.5)", zIndex: 9999 }}>
      <div style={{ background: "white", padding: 24, borderRadius: 8, width: 520, maxWidth: "96%" }}>
        <h3>メール認証コードの送信</h3>
        <p style={{ color: "#374151" }}>送信先: {email}</p>

        {status === null && (
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={sendOtp} style={{ padding: "8px 12px" }}>送信</button>
            <button onClick={onClose} style={{ padding: "8px 12px" }}>キャンセル</button>
          </div>
        )}

        {status === "sending" && <p>送信中…</p>}
        {status === "sent" && (
          <div>
            <p>認証コードを送信しました。メールに届いた6桁のコードを入力してください。</p>
            <OTPInput onComplete={handleComplete} />
            <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
              <button onClick={sendOtp} style={{ padding: "8px 12px" }}>再送</button>
              <button onClick={onClose} style={{ padding: "8px 12px" }}>閉じる</button>
            </div>
          </div>
        )}

        {status === "verifying" && <p>確認中…</p>}

        {status === "verified" && (
          <div>
            <p style={{ color: "green" }}>認証に成功しました。</p>
            {inviteUrl ? (
              <p>Discord招待: <a href={inviteUrl} target="_blank" rel="noreferrer">{inviteUrl}</a></p>
            ) : (
              <p>招待リンクはまもなく届きます。</p>
            )}
            <div style={{ marginTop: 12 }}>
              <button onClick={onClose} style={{ padding: "8px 12px" }}>閉じる</button>
            </div>
          </div>
        )}

        {error && <p style={{ color: "#b91c1c" }}>エラー: {error}</p>}
      </div>
    </div>
  );
}
