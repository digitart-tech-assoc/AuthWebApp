"use client";

import Link from "next/link";
import { useState } from "react";
import OTPModal from "../../../../components/OTPModal";
import styles from "../../../join/join.module.css";

export default function ProspectiveStudentFormPage() {
  const [year, setYear] = useState("");
  const [yearTouched, setYearTouched] = useState(false);

  const [email, setEmail] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [emailChecking, setEmailChecking] = useState(false);
  const [emailExists, setEmailExists] = useState<boolean | null>(null);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [confirmEmailTouched, setConfirmEmailTouched] = useState(false);
  const [showOtp, setShowOtp] = useState(false);
  const [otpEmail, setOtpEmail] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const isYearValid = year.length === 0 || /^[0-9]+$/.test(year);

  const emailFormatValid = (value: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  };

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
    if (hasMx === null) {
      setEmailExists(null);
    } else {
      setEmailExists(Boolean(hasMx));
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>仮入会フォーム（青山学院大学入学見込み）</h1>
      </section>

      <section className={styles.card} style={{ marginBottom: 16 }}>
        <h2 className={styles.cardTitle}>入会の流れ</h2>
        <ol style={{ margin: 0, paddingLeft: 18, color: "#475569", lineHeight: 1.6 }}>
          <li>必要事項（氏名、メールアドレス 等）を入力して「送信」を押してください。</li>
          <li>入力したメールアドレス宛に認証パスワード（ワンタイムコード）を送信します。</li>
          <li>メールに届いた認証パスワードをこのページの確認欄に入力して検証してください。</li>
          <li>検証成功後、Discord招待リンクが発行されます。リンクからサーバーに参加してください。</li>
        </ol>
      </section>

      <section className={styles.card}>
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>氏名<span className={styles.required}>*</span></label>
            <input className={styles.input} placeholder="例: 山田 花子" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>メールアドレス<span className={styles.required}>*</span></label>
            <input
              className={styles.input}
              type="email"
              placeholder="example@mail.com"
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
              placeholder="example@mail.com"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              onBlur={() => setConfirmEmailTouched(true)}
              inputMode="email"
              aria-invalid={confirmEmailTouched && (confirmEmail !== email || !emailFormatValid(confirmEmail))}
              aria-describedby="confirm-email-help"
            />
            {confirmEmailTouched && confirmEmail !== email ? (
              <p className={styles.errorText} id="confirm-email-help">メールアドレスが一致しません。</p>
            ) : confirmEmailTouched && !emailFormatValid(confirmEmail) ? (
              <p className={styles.errorText} id="confirm-email-help">確認用メールアドレスの形式が正しくありません。</p>
            ) : (
              <p className={styles.helperText} id="confirm-email-help">上と同じメールアドレスを再入力してください。</p>
            )}
          </div>
          <div className={styles.field}>
            <label className={styles.label}>入学予定年度</label>
            <input
              className={styles.input}
              placeholder="例: 2027"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              onBlur={() => setYearTouched(true)}
              inputMode="numeric"
              pattern="\d*"
              aria-invalid={!isYearValid}
              aria-describedby="year-help"
            />
            {!isYearValid && yearTouched ? (
              <p className={styles.errorText} id="year-help">
                入学予定年度は半角数字のみで入力してください（例: 2027）。
              </p>
            ) : (
              <p className={styles.helperText} id="year-help">
                半角数字で入力してください（例: 2027）。任意入力です。
              </p>
            )}
          </div>
          <div className={styles.field}>
            <label className={styles.label}>質問等</label>
            <textarea className={styles.textarea} placeholder="質問、連絡事項等あればご記入ください" />
          </div>
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.primary}
              onClick={() => {
                console.log("送信ボタン押下", { email, confirmEmail });
                setFormError(null);
                setEmailTouched(true);
                setConfirmEmailTouched(true);
                if (!email || !confirmEmail) {
                  setFormError("メールアドレスと確認用欄を入力してください。");
                  return;
                }
                if (email !== confirmEmail) {
                  setFormError("メールアドレスが一致しません。");
                  return;
                }
                setOtpEmail(email);
                setShowOtp(true);
              }}
            >
              送信
            </button>
            <Link className={styles.secondary} href="/join/form">区分選択に戻る</Link>
          </div>
        </form>
      </section>
      {showOtp && (
        <OTPModal email={otpEmail} name="" formType="prospective-student" onClose={() => setShowOtp(false)} />
      )}
      {formError && <p style={{ color: "#b91c1c", marginTop: 8 }}>{formError}</p>}
    </main>
  );
}

