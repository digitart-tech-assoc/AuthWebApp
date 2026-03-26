"use client";

import { useState } from "react";
import styles from "../join/join.module.css";
import { submitContact } from "@/actions/contact";

export default function ContactPage() {
  const [email, setEmail] = useState("");
  const [confirmEmail, setConfirmEmail] = useState("");
  const [name, setName] = useState("");
  const [affiliation, setAffiliation] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  
  const [emailTouched, setEmailTouched] = useState(false);
  const [confirmTouched, setConfirmTouched] = useState(false);
  const [emailChecking, setEmailChecking] = useState(false);
  const [emailExists, setEmailExists] = useState<boolean | null>(null);
  
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  async function handleSubmit() {
    console.log("contact 送信ボタン押下");
    setFormError(null);
    setFormSuccess(null);
    setEmailTouched(true);
    setConfirmTouched(true);
    
    // バリデーション
    if (!email || !confirmEmail) {
      setFormError("メールアドレスと確認用欄を入力してください。");
      return;
    }
    if (email !== confirmEmail) {
      setFormError("メールアドレスが一致しません。");
      return;
    }
    if (!emailFormatValid(email)) {
      setFormError("メールアドレスの形式が正しくありません。");
      return;
    }
    if (!name.trim()) {
      setFormError("氏名を入力してください。");
      return;
    }
    
    setIsSubmitting(true);
    try {
      const result = await submitContact({
        email,
        name: name.trim(),
        subject: subject.trim() || null,
        affiliation: affiliation.trim() || null,
        message: message.trim() || null,
      });
      
      console.log("contact submitted successfully:", result);
      
      // フォームをリセット
      setEmail("");
      setConfirmEmail("");
      setName("");
      setAffiliation("");
      setSubject("");
      setMessage("");
      setEmailExists(null);
      
      setFormSuccess("お問い合わせを送信しました。返信までしばらくお待ちください。");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "送信に失敗しました";
      console.error("Failed to submit contact:", error);
      setFormError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>お問い合わせフォーム</h1>
        <p className={styles.lead}>お気軽にお問い合わせください。</p>
      </section>

      <section className={styles.card}>
        <form className={styles.form} onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
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
            <input 
              className={styles.input} 
              placeholder="例: 田中 / たなか123"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>所属</label>
            <input 
              className={styles.input} 
              placeholder="例: 青山学院大学 理工学部"
              value={affiliation}
              onChange={(e) => setAffiliation(e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>件名</label>
            <input 
              className={styles.input} 
              placeholder="お問い合わせの件名"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>本文</label>
            <textarea 
              className={styles.textarea} 
              placeholder="お問い合わせ内容をご記入ください"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>

          <div className={styles.actions}>
            <button
              type="submit"
              className={styles.primary}
              disabled={isSubmitting}
            >
              {isSubmitting ? "送信中…" : "送信"}
            </button>
          </div>
        </form>
        
        {formError && (
          <p style={{ color: "#b91c1c", marginTop: 16, fontSize: 14 }}>
            ❌ {formError}
          </p>
        )}
        {formSuccess && (
          <p style={{ color: "#15803d", marginTop: 16, fontSize: 14 }}>
            ✅ {formSuccess}
          </p>
        )}
      </section>
    </main>
  );
}
