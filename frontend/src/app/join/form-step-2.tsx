"use client";

import { useState } from "react";
import styles from "./join.module.css";

interface FormData {
  student_number: string;
  name: string;
  furigana: string;
  department: string;
  gender: string | null;
  phone: string;
}

interface FormStep2Props {
  initialData: FormData;
  hasExistingProfile: boolean;
  onContinue: (data: FormData) => void;
  onBack: () => void;
}

const DEPARTMENTS = [
  "経営学部経営学科",
  "経営学部組織内情報学科",
  "文学部日本文学科",
  "文学部英米文学科",
  "文学部フランス文学科",
  "文学部ドイツ文学科",
  "文学部歴史学科",
  "文学部世界史学科",
  "文学部日本史学科",
  "文学部地理学科",
  "理工学部電気電子工学科",
  "理工学部機械創造工学科",
  "理工学部情報テクノロジー学科",
  "理工学部システムデザイン工学科",
  "理工学部化学・生命科学科",
  "教育学部教育学科",
  "総合文化政策学部総合文化政策学科",
  "社会ネットワーク学部社会ネットワーク学科",
];

export default function FormStep2Input({
  initialData,
  hasExistingProfile,
  onContinue,
  onBack,
}: FormStep2Props) {
  const [formData, setFormData] = useState<FormData>(initialData);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.student_number.match(/^[Aa]\d{7}$/)) {
      newErrors.student_number = "学生番号は A で始まり7桁の数字です (例: A2312345)";
    }

    if (formData.name.trim().length === 0) {
      newErrors.name = "名前を入力してください";
    }

    if (formData.furigana.trim().length === 0) {
      newErrors.furigana = "ふりがなを入力してください";
    }

    if (formData.department.trim().length === 0) {
      newErrors.department = "学部学科を選択してください";
    }

    if (!formData.phone.match(/^\d{10,11}$/)) {
      newErrors.phone = "電話番号は 10 〜 11 桁の数字です";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onContinue(formData);
    }
  };

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>個人情報入力</h2>
      
      {hasExistingProfile && (
        <div
          style={{
            padding: "12px",
            background: "#dbeafe",
            color: "#1e40af",
            borderRadius: "6px",
            marginBottom: "16px",
            fontSize: "14px",
          }}
        >
          💡 Pre-member として登録済みの情報を自動入力しました。変更があれば編集してください。
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ marginTop: "16px" }}>
        {/* 学生番号 */}
        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="student_number" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
            学生番号 <span style={{ color: "#dc2626" }}>*</span>
          </label>
          <input
            id="student_number"
            type="text"
            placeholder="A2312345"
            value={formData.student_number}
            onChange={(e) =>
              setFormData({ ...formData, student_number: e.target.value.toUpperCase() })
            }
            style={{
              width: "100%",
              padding: "8px 12px",
              border: errors.student_number ? "2px solid #dc2626" : "1px solid #cbd5e1",
              borderRadius: "6px",
              fontSize: "14px",
              boxSizing: "border-box",
            }}
          />
          {errors.student_number && (
            <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
              {errors.student_number}
            </p>
          )}
        </div>

        {/* 名前 */}
        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="name" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
            名前 <span style={{ color: "#dc2626" }}>*</span>
          </label>
          <input
            id="name"
            type="text"
            placeholder="山田太郎"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            style={{
              width: "100%",
              padding: "8px 12px",
              border: errors.name ? "2px solid #dc2626" : "1px solid #cbd5e1",
              borderRadius: "6px",
              fontSize: "14px",
              boxSizing: "border-box",
            }}
          />
          {errors.name && (
            <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
              {errors.name}
            </p>
          )}
        </div>

        {/* ふりがな */}
        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="furigana" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
            ふりがな <span style={{ color: "#dc2626" }}>*</span>
          </label>
          <input
            id="furigana"
            type="text"
            placeholder="やまだたろう"
            value={formData.furigana}
            onChange={(e) => setFormData({ ...formData, furigana: e.target.value })}
            style={{
              width: "100%",
              padding: "8px 12px",
              border: errors.furigana ? "2px solid #dc2626" : "1px solid #cbd5e1",
              borderRadius: "6px",
              fontSize: "14px",
              boxSizing: "border-box",
            }}
          />
          {errors.furigana && (
            <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
              {errors.furigana}
            </p>
          )}
        </div>

        {/* 学部学科 */}
        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="department" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
            学部学科 <span style={{ color: "#dc2626" }}>*</span>
          </label>
          <select
            id="department"
            value={formData.department}
            onChange={(e) => setFormData({ ...formData, department: e.target.value })}
            style={{
              width: "100%",
              padding: "8px 12px",
              border: errors.department ? "2px solid #dc2626" : "1px solid #cbd5e1",
              borderRadius: "6px",
              fontSize: "14px",
              boxSizing: "border-box",
            }}
          >
            <option value="">選択してください</option>
            {DEPARTMENTS.map((dept) => (
              <option key={dept} value={dept}>
                {dept}
              </option>
            ))}
          </select>
          {errors.department && (
            <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
              {errors.department}
            </p>
          )}
        </div>

        {/* 性別 */}
        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: "600" }}>
            性別
          </label>
          <div style={{ display: "flex", gap: "16px" }}>
            {["male", "female", "other"].map((option) => (
              <label key={option} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <input
                  type="radio"
                  name="gender"
                  value={option}
                  checked={formData.gender === option}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                />
                <span>
                  {option === "male" ? "男性" : option === "female" ? "女性" : "その他"}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* 電話番号 */}
        <div style={{ marginBottom: "24px" }}>
          <label htmlFor="phone" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
            電話番号 <span style={{ color: "#dc2626" }}>*</span>
          </label>
          <input
            id="phone"
            type="tel"
            placeholder="09012345678"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            style={{
              width: "100%",
              padding: "8px 12px",
              border: errors.phone ? "2px solid #dc2626" : "1px solid #cbd5e1",
              borderRadius: "6px",
              fontSize: "14px",
              boxSizing: "border-box",
            }}
          />
          {errors.phone && (
            <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
              {errors.phone}
            </p>
          )}
        </div>

        {/* ボタン */}
        <div style={{ display: "flex", gap: "12px", justifyContent: "space-between" }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              padding: "12px 24px",
              background: "#e5e7eb",
              color: "#1f2937",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "16px",
              fontWeight: "600",
            }}
          >
            ← 戻る
          </button>
          <button
            type="submit"
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
        </div>
      </form>
    </div>
  );
}
