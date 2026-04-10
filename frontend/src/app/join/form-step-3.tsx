"use client";

import { useState } from "react";
import styles from "./join.module.css";

interface SurveyAnswers {
  digitart_channels: string[];
  digitart_channels_other: string;
  circle_search_channels: string[];
  circle_search_other: string;
  discord_invite_other: string;
  discord_invite_source: string | null;
  interested_fields: string[];
  interested_fields_other: string;
  motivations: string[];
  motivations_other: string;
}

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
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>アンケート</h2>

      <div style={{ marginTop: 12 }}>
        {/* 1. Digitartの認知経路 */}
        <section style={{ marginBottom: 20 }}>
          <h3 className={styles.qTitle}>1. Digitartの認知経路</h3>
          <p className={styles.qDesc}>Digitartをどのようにして知りましたか？(複数選択可)</p>
          <div className={styles.optionList}>
            {OPTIONS_A.map((opt) => (
              <label key={opt} className={styles.optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.digitart_channels.includes(opt)}
                  onChange={() => toggleMulti("digitart_channels", opt)}
                />
                <span className={styles.optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.digitart_channels_other}
                      onChange={(e) => setAnswers({ ...answers, digitart_channels_other: e.target.value })}
                      className={styles.optionOtherInline}
                      aria-invalid={digitartOtherMissing}
                    />
                    {digitartOtherMissing && (
                      <p className={styles.errorText} style={{ marginTop: 6 }}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 2. サークルの認知経路 */}
        <section style={{ marginBottom: 20 }}>
          <h3 className={styles.qTitle}>2. サークルの認知経路</h3>
          <p className={styles.qDesc}>サークルを探す際になにを使いましたか？(複数選択可)</p>
          <div className={styles.optionList}>
            {OPTIONS_A.map((opt) => (
              <label key={opt + "2"} className={styles.optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.circle_search_channels.includes(opt)}
                  onChange={() => toggleMulti("circle_search_channels", opt)}
                />
                <span className={styles.optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.circle_search_other}
                      onChange={(e) => setAnswers({ ...answers, circle_search_other: e.target.value })}
                      className={styles.optionOtherInline}
                      aria-invalid={circleOtherMissing}
                    />
                    {circleOtherMissing && (
                      <p className={styles.errorText} style={{ marginTop: 6 }}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 3. Discordへの参加経路 */}
        <section style={{ marginBottom: 20 }}>
          <h3 className={styles.qTitle}>3. Discordへの参加経路</h3>
          <p className={styles.qDesc}>Discordサーバーの招待はどこでもらいましたか？</p>
          <div className={styles.optionList}>
            {OPTIONS_DISCORD.map((opt) => (
              <label key={opt} className={styles.optionLabel}>
                <input
                  type="radio"
                  name="discord_source"
                  checked={answers.discord_invite_source === opt}
                  onChange={() => setAnswers({ ...answers, discord_invite_source: opt })}
                />
                <span className={styles.optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.discord_invite_other}
                      onChange={(e) => setAnswers({ ...answers, discord_invite_other: e.target.value })}
                      className={styles.optionOtherInline}
                      aria-invalid={discordOtherMissing}
                    />
                    {discordOtherMissing && (
                      <p className={styles.errorText} style={{ marginTop: 6 }}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 4. 希望する活動分野 */}
        <section style={{ marginBottom: 20 }}>
          <h3 className={styles.qTitle}>4. 希望する活動分野</h3>
          <p className={styles.qDesc}>主に興味のある活動分野はなんですか？(複数選択可)</p>
          <div className={styles.optionList}>
            {OPTIONS_FIELDS.map((opt) => (
              <label key={opt} className={styles.optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.interested_fields.includes(opt)}
                  onChange={() => toggleMulti("interested_fields", opt)}
                />
                <span className={styles.optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.interested_fields_other}
                      onChange={(e) => setAnswers({ ...answers, interested_fields_other: e.target.value })}
                      className={styles.optionOtherInline}
                      aria-invalid={fieldsOtherMissing}
                    />
                    {fieldsOtherMissing && (
                      <p className={styles.errorText} style={{ marginTop: 6 }}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        {/* 5. 活動目的 */}
        <section style={{ marginBottom: 20 }}>
          <h3 className={styles.qTitle}>5. 活動目的</h3>
          <p className={styles.qDesc}>当サークルに参加する主な目的は何ですか？(複数選択可)</p>
          <div className={styles.optionList}>
            {OPTIONS_MOTIVATION.map((opt) => (
              <label key={opt} className={styles.optionLabel}>
                <input
                  type="checkbox"
                  checked={answers.motivations.includes(opt)}
                  onChange={() => toggleMulti("motivations", opt)}
                />
                <span className={styles.optionText}>{opt}</span>
                {opt === "その他" && (
                  <>
                    <input
                      placeholder="その他を記入"
                      value={answers.motivations_other}
                      onChange={(e) => setAnswers({ ...answers, motivations_other: e.target.value })}
                      className={styles.optionOtherInline}
                      aria-invalid={motivationsOtherMissing}
                    />
                    {motivationsOtherMissing && (
                      <p className={styles.errorText} style={{ marginTop: 6 }}>「その他」を入力してください</p>
                    )}
                  </>
                )}
              </label>
            ))}
          </div>
        </section>

        <div className={styles.surveyFooter}>
          <button onClick={onBack} className={styles.secondary} style={{ padding: "10px 18px" }}>← 戻る</button>

          <button
            onClick={handleNext}
            className={styles.primary}
            style={{ padding: "10px 18px" }}
            disabled={hasOtherErrors}
          >
            次へ
          </button>
        </div>
      </div>
    </div>
  );
}
