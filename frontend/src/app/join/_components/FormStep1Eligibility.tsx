"use client";

import type { EligibilityCheckResult } from "@/types/join";
import { alertError, alertSuccess, alertWarning, btnPrimary, card, cardTitle, textLink } from "./joinStyles";

interface FormStep1Props {
  eligibility: EligibilityCheckResult | null;
  onContinue: () => void;
}

function statusClass(ok: boolean): string {
  return ok ? "font-medium text-emerald-700" : "font-medium text-red-700";
}

export default function FormStep1Eligibility({
  eligibility,
  onContinue,
}: FormStep1Props) {
  const canContinue = eligibility?.can_register ?? false;

  return (
    <div className={card}>
      <h2 className={cardTitle}>入会資格確認</h2>

      {eligibility && (
        <div className="mt-4 text-sm text-slate-700">
          <div className="mb-4 space-y-3">
            <p>
              <strong className="text-slate-900">Discord ログイン:</strong>{" "}
              <span className={statusClass(eligibility.is_discord_linked)}>
                {eligibility.is_discord_linked ? "✓ 確認済み" : "✗ 未リンク"}
              </span>
            </p>

            <p>
              <strong className="text-slate-900">Pre-member 登録:</strong>{" "}
              <span className={statusClass(eligibility.is_pre_member)}>
                {eligibility.is_pre_member ? "✓ 登録済み" : "✗ 未登録"}
              </span>
            </p>

            <p>
              <strong className="text-slate-900">支払済み確認:</strong>{" "}
              <span className={statusClass(eligibility.is_paid)}>
                {eligibility.is_paid ? "✓ 確認済み" : "✗ 未確認"}
              </span>
            </p>
          </div>

          {eligibility.is_pre_member ? (
            <>
              <div className={`${canContinue ? alertSuccess : alertError} mb-4`}>
                <p>{eligibility.reason}</p>
              </div>

              {canContinue && (
                <button type="button" onClick={onContinue} className={btnPrimary}>
                  続行 →
                </button>
              )}
            </>
          ) : (
            <div className="mt-3">
              <div className={`${alertWarning} mb-3`}>
                <p className="m-0">
                  現在、入会予定者リストに登録されていません。
                </p>
              </div>

              <div className="space-y-2 leading-relaxed">
                <p className="m-0">
                  - 初めてこのサークルに参加する方は、まず <a href="/join/form" className={textLink}>仮入会フォーム</a> からお申込みください。
                </p>

                <p className="m-0">
                  - 本入会（こちらの本入会フォーム）は、<strong className="text-slate-900">入会費をお支払いのうえ</strong> ご入力いただく必要があります。
                </p>

                <p className="m-0">
                  - すでに入会費をお支払い済みでこの表示が出る場合は、<a href="/contact" className={textLink}>幹部会までお問い合わせ</a>ください。
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
