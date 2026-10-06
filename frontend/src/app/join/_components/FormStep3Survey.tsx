"use client";

import { useState } from "react";
import { btnPrimary, btnSecondary, card, cardTitle, fieldError } from "./joinStyles";

import type { SurveyAnswers } from "@/types/join";

const sectionClass = "mb-5";
const qTitle = "mb-1.5 text-base font-semibold text-slate-900";
const qDesc = "mb-2.5 text-sm text-slate-500";
const optionList = "mb-2 flex flex-col gap-2 pl-3.5";
const optionLabel = "flex min-h-10 items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors hover:bg-slate-50";
const optionText = "shrink-0 text-sm text-slate-900";
const optionOtherInline =
  "ml-2 min-w-40 rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20";

interface Props {
  onBack: () => void;
  onComplete: (answers?: SurveyAnswers) => void;
}

const OPTIONS_A = [
  "新歓イベント(対面説明会)",
  "公式SNS(X/Instagram)",
  "公式ウェブサイト",
  "非公式SNS/ウェブサイト",
  "大学アプリ・掲示板",
  "先輩・友人からの紹介",
  "その他",
];

const OPTIONS_DISCORD = [
  "新歓イベント(QRコード)",
  "新歓イベント(SNSにDM)",
  "公式SNSでのDM",
  "仮入会フォーム(ウェブサイト)",
  "その他",
];

const OPTIONS_FIELDS = [
  "Web アプリ開発",
  "ゲーム開発",
  "AI/ML",
  "グラフィックス/3Dモデリング",
  "デザイン/イラスト",
  "サウンド",
  "特に決めていない",
  "その他",
];

const OPTIONS_MOTIVATION = [
  "スキルアップ・学習",
  "同じ興味を持つメンバーとの交流",
  "プロジェクト・作品制作",
  "将来のキャリアに活かしたい",
  "趣味として楽しみたい",
  "その他",
];

export default function FormStep3Survey({ onBack, onComplete }: Props) {
  const [answers, setAnswers] = useState<SurveyAnswers>({
    digitart_channels: [],
    digitart_channels_other: "",
    circle_search_channels: [],
    circle_search_other: "",
    discord_invite_other: "",
    discord_invite_source: null,
    interested_fields: [],
    interested_fields_other: "",
    motivations: [],
    motivations_other: "",
  });

  const toggleMulti = (key: keyof SurveyAnswers, value: string) => {
    setAnswers((prev) => {
      const arr = (prev[key] as unknown as string[]) || [];
      const exists = arr.includes(value);
      const next = exists ? arr.filter((v) => v !== value) : [...arr, value];
      return { ...prev, [key]: next } as SurveyAnswers;
    });
  };

  const digitartOtherMissing = answers.digitart_channels.includes("その他") && answers.digitart_channels_other.trim() === "";
  const circleOtherMissing = answers.circle_search_channels.includes("その他") && answers.circle_search_other.trim() === "";
  const discordOtherMissing = answers.discord_invite_source === "その他" && answers.discord_invite_other.trim() === "";
  const fieldsOtherMissing = answers.interested_fields.includes("その他") && answers.interested_fields_other.trim() === "";
  const motivationsOtherMissing = answers.motivations.includes("その他") && answers.motivations_other.trim() === "";

  const hasOtherErrors = digitartOtherMissing || circleOtherMissing || discordOtherMissing || fieldsOtherMissing || motivationsOtherMissing;

  const handleNext = () => {
    if (hasOtherErrors) return;
    onComplete(answers);
  };

  return (
    <div className={card}>
      <h2 className={cardTitle}>アンケート</h2>

      <div className="mt-3">
        {/* 1. Digitartの認知経路 */}
        <section className={sectionClass}>
          <h3 className={qTitle}>1. Digitartの認知経路</h3>
          <p className={qDesc}>Digitartをどのようにして知りましたか？(複数選択可)</p>
          <div className={optionList}>
            {OPTIONS_A.map((opt) => (
              <label key={opt} className={optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.digitart_channels.includes(opt)}
                  onChange={() => toggleMulti("digitart_channels", opt)}
                />
                <span className={optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.digitart_channels_other}
                      onChange={(e) => setAnswers({ ...answers, digitart_channels_other: e.target.value })}
                      className={optionOtherInline}
                      aria-invalid={digitartOtherMissing}
                    />
                    {digitartOtherMissing && (
                      <p className={`${fieldError} mt-1.5`}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 2. サークルの認知経路 */}
        <section className={sectionClass}>
          <h3 className={qTitle}>2. サークルの認知経路</h3>
          <p className={qDesc}>サークルを探す際になにを使いましたか？(複数選択可)</p>
          <div className={optionList}>
            {OPTIONS_A.map((opt) => (
              <label key={opt + "2"} className={optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.circle_search_channels.includes(opt)}
                  onChange={() => toggleMulti("circle_search_channels", opt)}
                />
                <span className={optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.circle_search_other}
                      onChange={(e) => setAnswers({ ...answers, circle_search_other: e.target.value })}
                      className={optionOtherInline}
                      aria-invalid={circleOtherMissing}
                    />
                    {circleOtherMissing && (
                      <p className={`${fieldError} mt-1.5`}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 3. Discordへの参加経路 */}
        <section className={sectionClass}>
          <h3 className={qTitle}>3. Discordへの参加経路</h3>
          <p className={qDesc}>Discordサーバーの招待はどこでもらいましたか？</p>
          <div className={optionList}>
            {OPTIONS_DISCORD.map((opt) => (
              <label key={opt} className={optionLabel}>
                <input
                  type="radio"
                  name="discord_source"
                  checked={answers.discord_invite_source === opt}
                  onChange={() => setAnswers({ ...answers, discord_invite_source: opt })}
                />
                <span className={optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.discord_invite_other}
                      onChange={(e) => setAnswers({ ...answers, discord_invite_other: e.target.value })}
                      className={optionOtherInline}
                      aria-invalid={discordOtherMissing}
                    />
                    {discordOtherMissing && (
                      <p className={`${fieldError} mt-1.5`}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 4. 希望する活動分野 */}
        <section className={sectionClass}>
          <h3 className={qTitle}>4. 希望する活動分野</h3>
          <p className={qDesc}>主に興味のある活動分野はなんですか？(複数選択可)</p>
          <div className={optionList}>
            {OPTIONS_FIELDS.map((opt) => (
              <label key={opt} className={optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.interested_fields.includes(opt)}
                  onChange={() => toggleMulti("interested_fields", opt)}
                />
                <span className={optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.interested_fields_other}
                      onChange={(e) => setAnswers({ ...answers, interested_fields_other: e.target.value })}
                      className={optionOtherInline}
                      aria-invalid={fieldsOtherMissing}
                    />
                    {fieldsOtherMissing && (
                      <p className={`${fieldError} mt-1.5`}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 5. 活動目的 */}
        <section className={sectionClass}>
          <h3 className={qTitle}>5. 活動目的</h3>
          <p className={qDesc}>当サークルに参加する主な目的は何ですか？(複数選択可)</p>
          <div className={optionList}>
            {OPTIONS_MOTIVATION.map((opt) => (
              <label key={opt} className={optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.motivations.includes(opt)}
                  onChange={() => toggleMulti("motivations", opt)}
                />
                <span className={optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.motivations_other}
                      onChange={(e) => setAnswers({ ...answers, motivations_other: e.target.value })}
                      className={optionOtherInline}
                      aria-invalid={motivationsOtherMissing}
                    />
                    {motivationsOtherMissing && (
                      <p className={`${fieldError} mt-1.5`}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        <div className="mt-5 flex justify-between gap-3 border-t border-slate-200 pt-3">
          <button type="button" onClick={onBack} className={btnSecondary}>← 戻る</button>

          <button
            type="button"
            onClick={handleNext}
            className={btnPrimary}
            disabled={hasOtherErrors}
          >
            次へ
          </button>
        </div>
      </div>
    </div>
  );
}
