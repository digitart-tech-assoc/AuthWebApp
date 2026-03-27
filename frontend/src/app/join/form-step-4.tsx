"use client";

import Link from "next/link";
import styles from "./join.module.css";

interface FormStep4Props {
  studentNumber: string;
  name: string;
  onComplete: () => void;
}

export default function FormStep4Complete({
  studentNumber,
  name,
  onComplete,
}: FormStep4Props) {
  return (
    <div className={styles.card}>
      <div style={{ textAlign: "center", padding: "32px 16px" }}>
        <div style={{ fontSize: "48px", marginBottom: "16px" }}>✅</div>

        <h2 style={{ fontSize: "24px", fontWeight: "700", marginBottom: "12px" }}>
          入会登録完了！
        </h2>

        <p style={{ fontSize: "16px", color: "#64748b", marginBottom: "24px" }}>
          {name} さん、本会員としての登録が完了しました。
        </p>

        <div
          style={{
            background: "#f8fafc",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "20px",
            marginBottom: "24px",
            textAlign: "left",
          }}
        >
          <h3 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "8px" }}>
            登録情報
          </h3>
          <p style={{ fontSize: "14px", color: "#475569", margin: "4px 0" }}>
            <strong>学生番号:</strong> {studentNumber}
          </p>
          <p style={{ fontSize: "14px", color: "#475569", margin: "4px 0" }}>
            <strong>名前:</strong> {name}
          </p>
        </div>

        <Link
          href="/contact"
          style={{
            display: "block",
            padding: "12px 32px",
            background: "#e5e7eb",
            color: "#1f2937",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "16px",
            fontWeight: "600",
            textDecoration: "none",
            width: "100%",
            maxWidth: "300px",
            margin: "0 auto",
            textAlign: "center",
          }}
        >
          お問い合わせ
        </Link>
      </div>
    </div>
  );
}
