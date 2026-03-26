"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import styles from "../../../join/join.module.css";
import OTPModal from "../../../../components/OTPModal";

const STUDENT_ID_PATTERN = /^[1234S][A-Za-z0-9]{7}$/;

function buildAoyamaEmail(studentId: string): string {
  const headMap: Record<string, string> = {
    "1": "a",
    "2": "b",
    "3": "c",
    "4": "d",
    S: "s",
  };

  const normalized = studentId.trim();
  const first = normalized.charAt(0).toUpperCase();
  const tail = normalized.slice(1).toLowerCase();
  const prefix = headMap[first];

  if (!prefix) {
    return "";
  }

  return `${prefix}${tail}@aoyama.ac.jp`;
}

export default function AoyamaStudentFormPage() {
  const [studentId, setStudentId] = useState("");
  const [showOtp, setShowOtp] = useState(false);
  const [otpEmail, setOtpEmail] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const normalizedStudentId = useMemo(() => studentId.trim(), [studentId]);
  const isStudentIdValid = STUDENT_ID_PATTERN.test(normalizedStudentId.toUpperCase());
  const autoCompletedEmail = isStudentIdValid ? buildAoyamaEmail(normalizedStudentId) : "";

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>仮入会フォーム（青山学院大学の学生）</h1>
        <p className={styles.lead}>モック画面です。実送信は未接続です。</p>
      </section>

      <section className={styles.card} style={{ marginBottom: 16 }}>
        <h2 className={styles.cardTitle}>仮入会の流れ</h2>
        <ol style={{ margin: 0, paddingLeft: 18, color: "#475569", lineHeight: 1.6 }}>
          <li>必要事項（氏名、学生番号 等）を入力して「送信」を押してください。</li>
          <li>入力したメールアドレス宛に認証パスワード（ワンタイムコード）を送信します。</li>
          <li>メールに届いた認証パスワードをこのページの確認欄に入力して検証してください。</li>
          <li>検証成功後、Discord招待リンクが発行されます。リンクからサーバーに参加してください。</li>
        </ol>
      </section>

      <section className={styles.card}>
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>氏名<span className={styles.required}>*</span></label>
            <input className={styles.input} placeholder="例: 山田 太郎" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>学生番号<span className={styles.required}>*</span></label>
            <input
              className={styles.input}
              placeholder="例: 1A234567"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              aria-invalid={!isStudentIdValid && normalizedStudentId.length > 0}
            />
            {!isStudentIdValid && normalizedStudentId.length > 0 ? (
              <p className={styles.errorText}>
                学生番号は先頭が 1 / 2 / 3 / 4 / S で、全8文字の英数字で入力してください。
              </p>
            ) : (
              <p className={styles.helperText}>
                入力形式に合致すると、メールアドレスを自動補完します。
              </p>
            )}
          </div>
          <div className={styles.field}>
            <label className={styles.label}>メールアドレス<span className={styles.required}>*</span></label>
            <input
              className={`${styles.input} ${styles.readOnlyInput}`}
              type="email"
              placeholder="学生番号から自動補完"
              value={autoCompletedEmail}
              readOnly
              aria-readonly="true"
              title="学生番号から自動補完されるため編集できません"
            />
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
                console.log("aoyama 送信ボタン押下", { studentId, autoCompletedEmail });
                setFormError(null);
                if (!isStudentIdValid) {
                  setFormError("学生番号が正しくありません。");
                  return;
                }
                if (!autoCompletedEmail) {
                  setFormError("自動補完されたメールアドレスが生成できません。");
                  return;
                }
                setOtpEmail(autoCompletedEmail);
                setShowOtp(true);
              }}
            >
              送信（モック）
            </button>
            <Link className={styles.secondary} href="/join/form">区分選択に戻る</Link>
          </div>
        </form>
      </section>
      {formError && <p style={{ color: "#b91c1c", marginTop: 8 }}>{formError}</p>}
      {showOtp && <OTPModal email={otpEmail} name="" formType="aoyama-student" onClose={() => setShowOtp(false)} />}
    </main>
  );
}
