"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Info } from "lucide-react";
import OTPModal from "../../../../components/OTPModal";
import NameInput from "../../../../components/forms/NameInput";
import StudentNumberInput from "../../../../components/forms/StudentNumberInput";

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
  const [name, setName] = useState("");
  const [showOtp, setShowOtp] = useState(false);
  const [otpEmail, setOtpEmail] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const normalizedStudentId = useMemo(() => studentId.trim(), [studentId]);
  const isStudentIdValid = STUDENT_ID_PATTERN.test(normalizedStudentId.toUpperCase());
  const autoCompletedEmail = isStudentIdValid ? buildAoyamaEmail(normalizedStudentId) : "";

  return (
    <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
      {/* ヒーロー部分 */}
      <section className="bg-gradient-to-br from-slate-50 via-white to-emerald-50 pt-10 pb-10 md:pt-10 md:pb-10 px-6">
        <div className="max-w-4xl mx-auto text-center space-y-6 md:space-y-8">
          <div className="inline-block">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-emerald-200/50 bg-emerald-50/50">
              <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
              <span className="text-sm font-semibold text-emerald-700">在学生向け</span>
            </div>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight">
            <span className="text-slate-900">仮入会フォーム</span>
          </h1>

        </div>
      </section>

      {/* メインコンテンツ */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          {/* ステップ説明 */}
          <div className="bg-emerald-50/50 border border-emerald-200 rounded-2xl p-8 md:p-10 mb-12">
            <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-3">
              <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              入会の流れ
            </h2>
            <ol className="space-y-3 ml-4 text-slate-700 leading-relaxed">
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm font-bold">1</span>
                <span>必要事項（氏名、学生番号 等）を入力して「送信」をクリックしてください。</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm font-bold">2</span>
                <span>入力したメールアドレス宛に認証パスワード（ワンタイムコード）を送信します。</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm font-bold">3</span>
                <span>メールに届いた認証パスワードをこのページの確認欄に入力して検証してください。</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm font-bold">4</span>
                <span>検証成功後、Discord招待リンクが発行されます。リンクからサーバーに参加してください。</span>
              </li>
            </ol>
          </div>

          {/* フォームカード */}
          <div className="bg-white rounded-2xl border border-slate-100 p-8 md:p-10 shadow-sm">
            <form className="space-y-6">
              {/* 氏名 */}
              <div className="space-y-2">
                <NameInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
                  placeholder="例: 山田 太郎"
                  value={name}
                  onChange={(v) => setName(v)}
                />
              </div>

              {/* 学生番号 */}
              <div className="space-y-2">
                <StudentNumberInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
                  placeholder="例: 1A234567"
                  value={studentId}
                  onChange={(v) => setStudentId(v)}
                  aria-invalid={!isStudentIdValid && normalizedStudentId.length > 0}
                />
                {!isStudentIdValid && normalizedStudentId.length > 0 ? (
                  <p className="text-sm text-red-600 flex items-start gap-2">
                    <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    先頭が 1 / 2 / 3 / 4 / S で、全8文字の英数字で入力してください。
                  </p>
                ) : (
                  <p className="text-sm text-slate-600 flex items-start gap-2">
                    <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-500" />
                    入力形式に合致すると、メールアドレスを自動補完します。
                  </p>
                )}
              </div>

              {/* メールアドレス */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">
                  メールアドレス<span className="text-red-600">*</span>
                </label>
                <input
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-600 bg-slate-50 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition cursor-not-allowed"
                  type="email"
                  placeholder="学生番号から自動補完"
                  value={autoCompletedEmail}
                  readOnly
                  title="学生番号から自動補完されるため編集できません"
                />
              </div>

              {/* 質問等 */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">
                  質問等
                </label>
                <textarea
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition resize-none"
                  placeholder="質問、連絡事項等あればご記入ください"
                  rows={4}
                />
              </div>

              {/* エラーメッセージ */}
              {formError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
                  <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <p className="text-red-700 font-medium">{formError}</p>
                </div>
              )}

              {/* ボタン */}
              <div className="flex flex-col gap-3 pt-4">
                <button
                  type="button"
                  className="w-full px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold rounded-lg hover:from-emerald-700 hover:to-teal-700 transition-all hover:shadow-lg active:scale-95"
                  onClick={() => {
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
                  送信
                </button>
                <Link
                  href="/join/form"
                  className="px-6 py-3 border border-slate-300 text-slate-900 font-semibold rounded-lg hover:bg-slate-50 transition-all text-center"
                >
                  区分選択に戻る
                </Link>
              </div>
            </form>
          </div>
        </div>
      </section>

      {showOtp && <OTPModal email={otpEmail} name={name} formType="aoyama-student" autoSend onClose={() => setShowOtp(false)} />}
    </main>
  );
}
