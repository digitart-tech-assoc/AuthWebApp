"use client";

import Link from "next/link";
import { useState } from "react";
import { Info, CheckCircle, FileText, AlertCircle, Loader } from "lucide-react";
import OTPModal from "../../../../components/OTPModal";
import NameInput from "../../../../components/forms/NameInput";
import TextInput from "../../../../components/forms/TextInput";
import { validateFullName } from "../../../../lib/validation";

export default function ProspectiveStudentFormPage() {
  const [year, setYear] = useState("");
  const [yearTouched, setYearTouched] = useState(false);

  const [name, setName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);

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
  const isNameValid = validateFullName(name);

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
    <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
      {/* ヒーロー部分 */}
      <section className="bg-gradient-to-br from-slate-50 via-white to-blue-50 pt-10 pb-10 md:pt-10 md:pb-10 px-6">
        <div className="max-w-4xl mx-auto text-center space-y-6 md:space-y-8">
          <div className="inline-block">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-blue-200/50 bg-blue-50/50">
              <CheckCircle className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-blue-700">入学見込み向け</span>
            </div>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight">
            <span className="text-slate-900">仮入会フォーム</span><br />
          </h1>
        </div>
      </section>

      {/* メインコンテンツ */}
      <section className="py-12 px-4">
        <div className="max-w-3xl mx-auto">
          {/* フォームカード */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6 md:p-8 shadow-sm mb-8">
            <form className="space-y-6">
              {/* 氏名 */}
              <div className="space-y-2">
                <NameInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="例: 山田 花子"
                  value={name}
                  onChange={(v) => setName(v)}
                  onBlur={() => setNameTouched(true)}
                />
              </div>

              {/* メールアドレス */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">
                  メールアドレス<span className="text-red-600">*</span>
                </label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  type="email"
                  placeholder="example@mail.com"
                  value={email}
                  onChange={(v) => { setEmail(v); setEmailExists(null); }}
                  onBlur={async () => { setEmailTouched(true); await validateEmail(email); }}
                  inputMode="email"
                  aria-invalid={emailTouched && !emailFormatValid(email)}
                  aria-describedby="email-help"
                />
                {emailTouched && !emailFormatValid(email) ? (
                  <p className="text-sm text-red-600 flex items-start gap-2" id="email-help">
                    <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-500" />
                    メールアドレスの形式が正しくありません。
                  </p>
                ) : emailChecking ? (
                  <p className="text-sm text-blue-600 flex items-start gap-2" id="email-help">
                    <Loader className="w-4 h-4 flex-shrink-0 mt-0.5 animate-spin" />
                    メールサーバーを確認中…
                  </p>
                ) : emailExists === true ? (
                  <p className="text-sm text-emerald-600 flex items-start gap-2" id="email-help">
                    <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    受信可能なドメインが見つかりました。
                  </p>
                ) : emailExists === false ? (
                  <p className="text-sm text-red-600 flex items-start gap-2" id="email-help">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    メールサーバーが見つかりません。ドメイン名を確認してください。
                  </p>
                ) : (
                  <p className="text-sm text-slate-600 flex items-start gap-2" id="email-help">
                    <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-500" />
                    入力後にドメインのMXレコードを確認します（ネットワークの影響で検証できない場合があります）。
                  </p>
                )}
              </div>

              {/* メールアドレス確認 */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">
                  メールアドレス（確認）<span className="text-red-600">*</span>
                </label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  type="email"
                  placeholder="example@mail.com"
                  value={confirmEmail}
                  onChange={(v) => setConfirmEmail(v)}
                  onBlur={() => setConfirmEmailTouched(true)}
                  inputMode="email"
                  aria-invalid={confirmEmailTouched && (confirmEmail !== email || !emailFormatValid(confirmEmail))}
                  aria-describedby="confirm-email-help"
                />
                {confirmEmailTouched && confirmEmail !== email ? (
                  <p className="text-sm text-red-600 flex items-start gap-2" id="confirm-email-help">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    メールアドレスが一致しません。
                  </p>
                ) : confirmEmailTouched && !emailFormatValid(confirmEmail) ? (
                  <p className="text-sm text-red-600 flex items-start gap-2" id="confirm-email-help">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    確認用メールアドレスの形式が正しくありません。
                  </p>
                ) : (
                  <p className="text-sm text-slate-600 flex items-start gap-2" id="confirm-email-help">
                    <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-500" />
                    上と同じメールアドレスを再入力してください。
                  </p>
                )}
              </div>

              {/* 入学予定年度 */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">
                  入学予定年度
                </label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="例: 2027"
                  value={year}
                  onChange={(v) => setYear(v)}
                  onBlur={() => setYearTouched(true)}
                  inputMode="numeric"
                  pattern="\d*"
                  aria-invalid={!isYearValid}
                  aria-describedby="year-help"
                />
                {!isYearValid && yearTouched ? (
                  <p className="text-sm text-red-600 flex items-start gap-2" id="year-help">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    入学予定年度は半角数字のみで入力してください(例: 2027)。
                  </p>
                ) : (
                  <p className="text-sm text-slate-600 flex items-start gap-2" id="year-help">
                    <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-500" />
                    半角数字で入力してください(例: 2027)。任意入力です。
                  </p>
                )}
              </div>

              {/* 質問等 */}
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">
                  質問等
                </label>
                <textarea
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
                  placeholder="質問、連絡事項等あればご記入ください"
                  rows={4}
                />
              </div>

              {/* エラーメッセージ */}
              {formError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-red-700 font-medium">{formError}</p>
                </div>
              )}

              {/* ボタン */}
              <div className="flex flex-col gap-3 pt-4">
                <button
                  type="button"
                  className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-lg hover:from-blue-700 hover:to-cyan-700 transition-all hover:shadow-lg active:scale-95"
                  disabled={!isNameValid || !email || !confirmEmail}
                  onClick={() => {
                    console.log("送信ボタン押下", { email, confirmEmail });
                    setFormError(null);
                    setEmailTouched(true);
                    setConfirmEmailTouched(true);
                    setNameTouched(true);
                    if (!isNameValid) {
                      setFormError("氏名は「姓<半角スペース>名」の形式で入力してください。");
                      return;
                    }
                    if (!email || !confirmEmail) {
                      setFormError("メールアドレスと確認用欄を入力してください。");
                      return;
                    }
                    if (email !== confirmEmail) {
                      setFormError("メールアドレスが一致しません。");
                      return;
                    }
                    if (!name) {
                      setFormError("氏名を入力してください。");
                      return;
                    }
                    setOtpEmail(email);
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

          {/* ステップ説明 */}
          <div className="bg-blue-50/50 border border-blue-200 rounded-2xl p-6 md:p-8 mt-6 mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-3">
              <FileText className="w-6 h-6 text-blue-600" />
              入会の流れ
            </h2>
            <ol className="space-y-3 ml-4 text-slate-700 leading-relaxed">
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">1</span>
                <span>必要事項（氏名、メールアドレス 等）を入力して「送信」をクリックしてください。</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">2</span>
                <span>入力したメールアドレス宛に認証パスワード（ワンタイムコード）を送信します。</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">3</span>
                <span>メールに届いた認証パスワードをこのページの確認欄に入力して検証してください。</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">4</span>
                <span>検証成功後、Discord招待リンクが発行されます。リンクからサーバーに参加してください。</span>
              </li>
            </ol>
          </div>

        </div>
      </section>
      {showOtp && (
        <OTPModal email={otpEmail} name={name} formType="prospective-student" onClose={() => setShowOtp(false)} />
      )}
    </main>
  );
}

