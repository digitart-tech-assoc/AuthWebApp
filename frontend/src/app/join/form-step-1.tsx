"use client";

import { type EligibilityCheckResult } from "@/actions/student-registration";
import styles from "./join.module.css";

interface FormStep1Props {
  eligibility: EligibilityCheckResult | null;
  onContinue: () => void;
}

export default function FormStep1Eligibility({
  eligibility,
  onContinue,
}: FormStep1Props) {
  const canContinue = eligibility?.can_register ?? false;

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>入会資格確認</h2>
      
      {eligibility && (
        <div style={{ marginTop: "16px" }}>
          <div style={{ marginBottom: "12px" }}>
            <p>
              <strong>Discord ログイン:</strong>{" "}
              <span
                style={{
                  color: eligibility.is_discord_linked ? "#16a34a" : "#dc2626",
                }}
              >
                {eligibility.is_discord_linked ? "✓ 確認済み" : "✗ 未リンク"}
              </span>
            </p>
          </div>

          <div style={{ marginBottom: "12px" }}>
            <p>
              <strong>Pre-member 登録:</strong>{" "}
              <span
                style={{
                  color: eligibility.is_pre_member ? "#16a34a" : "#dc2626",
                }}
              >
                {eligibility.is_pre_member ? "✓ 登録済み" : "✗ 未登録"}
              </span>
            </p>
          </div>

          <div style={{ marginBottom: "16px" }}>
            <p>
              <strong>支払済み確認:</strong>{" "}
              <span
                style={{
                  color: eligibility.is_paid ? "#16a34a" : "#dc2626",
                }}
              >
                {eligibility.is_paid ? "✓ 確認済み" : "✗ 未確認"}
              </span>
            </p>
          </div>

          {eligibility.is_pre_member ? (
            <>
              <div
                style={{
                  padding: "12px",
                  background: canContinue ? "#dcfce7" : "#fee2e2",
                  color: canContinue ? "#166534" : "#991b1b",
                  borderRadius: "6px",
                  marginBottom: "16px",
                }}
              >
                <p>{eligibility.reason}</p>
              </div>

              {canContinue && (
                <button
                  onClick={onContinue}
                  style={{
                    padding: "12px 24px",
                    background: "#3b82f6",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "16px",
                    fontWeight: "600",
                  }}
                >
                  続行 →
                </button>
              )}
            </>
          ) : (
            <div style={{ marginTop: 12 }}>
              <div style={{ padding: "12px", background: "#fff7ed", color: "#92400e", borderRadius: 6, marginBottom: 12 }}>
                <p style={{ margin: 0 }}>
                  現在、入会予定者リストに登録されていません。
                </p>
              </div>

              <div style={{ marginBottom: 8 }}>
                <p style={{ margin: 0 }}>
                  - 初めてこのサークルに参加する方は、まず <a href="/join/form" style={{ color: "#0ea5e9" }}>仮入会フォーム</a> からお申込みください。
                </p>
              </div>

              <div style={{ marginBottom: 8 }}>
                <p style={{ margin: 0 }}>
                  - 本入会（こちらの本入会フォーム）は、<strong>入会費をお支払いのうえ</strong> ご入力いただく必要があります。
                </p>
              </div>

              <div>
                <p style={{ margin: 0 }}>
                  - すでに入会費をお支払い済みでこの表示が出る場合は、<a href="/contact" style={{ color: "#0ea5e9" }}>幹部会までお問い合わせ</a>ください。
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
