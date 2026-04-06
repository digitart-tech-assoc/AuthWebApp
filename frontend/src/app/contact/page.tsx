"use client";

import { useState } from "react";
import { Mail, Info } from "lucide-react";
import { submitContact } from "@/actions/contact";
import NameInput from "@/components/forms/NameInput";
import { validateFullName } from "@/lib/validation";
import TextInput from "@/components/forms/TextInput";

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

  const isNameValid = validateFullName(name);

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
    if (!isNameValid) {
      setFormError("氏名は「姓<半角スペース>名」の形式で入力してください。");
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
    <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
      <section className="bg-gradient-to-br from-slate-50 via-white to-blue-50 pt-10 pb-10 md:pt-10 md:pb-10 px-6">
        <div className="max-w-4xl mx-auto text-center space-y-6 md:space-y-8">
          <div className="inline-block">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-blue-200/50 bg-blue-50/50">
              <Mail className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-blue-700">お問い合わせ</span>
            </div>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight">
            <span className="text-slate-900">お問い合わせフォーム</span>
          </h1>
          <p className="text-slate-700 max-w-2xl mx-auto">お気軽にお問い合わせください。運営より折り返しご連絡します。</p>
        </div>
      </section>

      <section className="py-12 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="bg-white rounded-2xl border border-slate-100 p-6 md:p-8 shadow-sm mb-8">
            <form className="space-y-6" onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
              <div className="space-y-2">
                <NameInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="例: 田中 太郎"
                  value={name}
                  onChange={(v) => setName(v)}
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">メールアドレス<span className="text-red-600">*</span></label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  type="email"
                  placeholder="返信に使用するメールアドレス"
                  value={email}
                  onChange={(v) => { setEmail(v); setEmailExists(null); }}
                  onBlur={async () => { setEmailTouched(true); await validateEmail(email); }}
                  inputMode="email"
                  aria-invalid={emailTouched && !emailFormatValid(email)}
                  aria-describedby="email-help"
                />
                <p className="text-sm text-slate-600 flex items-start gap-2" id="email-help">
                  <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-500" />
                  {emailTouched && !emailFormatValid(email) ? (
                    <span className="text-red-600">メールアドレスの形式が正しくありません。</span>
                  ) : emailChecking ? (
                    <span className="text-blue-600">メールサーバーを確認中…</span>
                  ) : emailExists === true ? (
                    <span className="text-emerald-600">受信可能なドメインが見つかりました。</span>
                  ) : emailExists === false ? (
                    <span className="text-red-600">メールサーバーが見つかりません。ドメイン名を確認してください。</span>
                  ) : (
                    <span>入力後にドメインのMXレコードを確認します（ネットワークの影響で検証できない場合があります）。</span>
                  )}
                </p>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">メールアドレス（確認）<span className="text-red-600">*</span></label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  type="email"
                  placeholder="確認のため再入力してください"
                  value={confirmEmail}
                  onChange={(v) => setConfirmEmail(v)}
                  onBlur={() => setConfirmTouched(true)}
                  inputMode="email"
                  aria-invalid={confirmTouched && (confirmEmail !== email || !emailFormatValid(confirmEmail))}
                  aria-describedby="confirm-email-help"
                />
                {confirmTouched && confirmEmail !== email ? (
                  <p className="text-sm text-red-600 flex items-start gap-2" id="confirm-email-help">メールアドレスが一致しません。</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">所属</label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500"
                  placeholder="例: 青山学院大学 理工学部"
                  value={affiliation}
                  onChange={(v) => setAffiliation(v)}
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">件名</label>
                <TextInput
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500"
                  placeholder="お問い合わせの件名"
                  value={subject}
                  onChange={(v) => setSubject(v)}
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-900">本文</label>
                <textarea
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition resize-none"
                  placeholder="お問い合わせ内容をご記入ください"
                  rows={6}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </div>

              {formError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
                  <Info className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-red-700 font-medium">{formError}</p>
                </div>
              )}
              {formSuccess && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex gap-3">
                  <Info className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <p className="text-emerald-700 font-medium">{formSuccess}</p>
                </div>
              )}

              <div className="flex flex-col gap-3 pt-4">
                <button
                  type="button"
                  className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-lg hover:from-blue-700 hover:to-cyan-700 transition-all hover:shadow-lg active:scale-95"
                  onClick={handleSubmit}
                  disabled={isSubmitting || !isNameValid}
                >
                  {isSubmitting ? "送信中…" : "送信"}
                </button>
              </div>
            </form>
          </div>

          <div className="bg-blue-50/50 border border-blue-200 rounded-2xl p-6 md:p-8 mt-6 mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-3">
              <Info className="w-6 h-6 text-blue-600" />
              よくある質問
            </h2>
            <ul className="space-y-3 ml-4 text-slate-700 leading-relaxed list-disc pl-5">
              <li>フォームが動作しない場合は aoyama.tech.exe@gmail.com までご連絡ください。</li>
              <li>返信まで数日かかる場合があります。件名に要点を明記してください。</li>
            </ul>
          </div>
        </div>
      </section>
    </main>
  );
}
