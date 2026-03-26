"use client";

import { useState } from "react";
import styles from "../join/join.module.css";

export default function ContactPage() {
  const [email, setEmail] = useState("");
  const [confirmEmail, setConfirmEmail] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [confirmTouched, setConfirmTouched] = useState(false);
  const [emailChecking, setEmailChecking] = useState(false);
  const [emailExists, setEmailExists] = useState<boolean | null>(null);

  const emailFormatValid = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  async function checkEmailMx(domain: string) {
    try {
      const url = `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(domain)}&type=MX`;
      const res = await fetch(url, { headers: { Accept: "application/dns-json" } });
      if (!res.ok) return null;
      const json = await res.json();
      return Array.isArray(json.Answer) && json.Answer.length > 0;
    } catch (e) {
      return null;
    }
  }

  async function validateEmail(value: string) {
    if (!emailFormatValid(value)) {
      setEmailExists(null);
      return;
    }
    const domain = value.split("@").slice(1).join("@");
    if (!domain) {
      setEmailExists(null);
      return;
    }
    setEmailChecking(true);
    const hasMx = await checkEmailMx(domain);
    setEmailChecking(false);
    if (hasMx === null) setEmailExists(null);
    else setEmailExists(Boolean(hasMx));
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>お問い合わせフォーム</h1>
        <p className={styles.lead}>入力項目は要件どおりに配置したモックです。実送信先は未接続です。</p>
      </section>

      <section className={styles.card}>
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>連絡先（メールアドレス）<span className={styles.required}>*</span></label>
            <input
              className={styles.input}
              type="email"
              placeholder="返信に使用するメールアドレス"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setEmailExists(null); }}
              onBlur={async () => { setEmailTouched(true); await validateEmail(email); }}
              inputMode="email"
              aria-invalid={emailTouched && !emailFormatValid(email)}
              aria-describedby="email-help"
            />
            {emailTouched && !emailFormatValid(email) ? (
              <p className={styles.errorText} id="email-help">メールアドレスの形式が正しくありません。</p>
            ) : emailChecking ? (
              <p className={styles.helperText} id="email-help">メールサーバーを確認しています…</p>
            ) : emailExists === true ? (
              <p className={styles.helperText} id="email-help">受信可能なドメインが見つかりました。</p>
            ) : emailExists === false ? (
              <p className={styles.errorText} id="email-help">メールサーバーが見つかりません。ドメイン名を確認してください。</p>
            ) : (
              <p className={styles.helperText} id="email-help">入力後にドメインのMXレコードを確認します（ネットワークの影響で検証できない場合があります）。</p>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>メールアドレス（確認）<span className={styles.required}>*</span></label>
            <input
              className={styles.input}
              type="email"
              placeholder="確認のため再入力してください"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              onBlur={() => setConfirmTouched(true)}
              inputMode="email"
              aria-invalid={confirmTouched && (confirmEmail !== email || !emailFormatValid(confirmEmail))}
              aria-describedby="confirm-email-help"
            />
            {confirmTouched && confirmEmail !== email ? (
              <p className={styles.errorText} id="confirm-email-help">メールアドレスが一致しません。</p>
            ) : confirmTouched && !emailFormatValid(confirmEmail) ? (
              <p className={styles.errorText} id="confirm-email-help">確認用メールアドレスの形式が正しくありません。</p>
            ) : (
              <p className={styles.helperText} id="confirm-email-help">上と同じメールアドレスを再入力してください。</p>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>氏名（ニックネーム可）<span className={styles.required}>*</span></label>
            <input className={styles.input} placeholder="例: 田中 / たなか123" required />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>所属</label>
            <input className={styles.input} placeholder="例: 青山学院大学 理工学部" />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>件名</label>
            <input className={styles.input} placeholder="お問い合わせの件名" />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>本文</label>
            <textarea className={styles.textarea} placeholder="お問い合わせ内容をご記入ください" />
          </div>

          <div className={styles.actions}>
            <button type="button" className={styles.primary}>送信（モック）</button>
          </div>
        </form>
      </section>
    </main>
  );
}
