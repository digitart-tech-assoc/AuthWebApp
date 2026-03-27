"use client";

import { useState } from "react";
import styles from "./join.module.css";
import StudentNumberInput from "@/components/forms/StudentNumberInput";
import NameInput from "@/components/forms/NameInput";
import FuriganaInput from "@/components/forms/FuriganaInput";
import DepartmentSelect from "@/components/forms/DepartmentSelect";
import GenderSelect from "@/components/forms/GenderSelect";
import PhoneInput from "@/components/forms/PhoneInput";
import { validateFullName } from "../../lib/validation";

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

    // 名前は姓と名の間に半角スペースを含み、ミドルネームも許容する正規表現で検証
    if (!validateFullName(formData.name)) {
      newErrors.name = "姓と名の間に半角スペースを入れてください（ミドルネームも許容）";
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
        <StudentNumberInput
          value={formData.student_number}
          onChange={(value) => setFormData({ ...formData, student_number: value })}
          error={errors.student_number}
        />

        <NameInput
          value={formData.name}
          onChange={(value) => setFormData({ ...formData, name: value })}
          error={errors.name}
        />

        <FuriganaInput
          value={formData.furigana}
          onChange={(value) => setFormData({ ...formData, furigana: value })}
          error={errors.furigana}
        />

        <DepartmentSelect
          value={formData.department}
          onChange={(value) => setFormData({ ...formData, department: value })}
          error={errors.department}
        />

        <GenderSelect
          value={formData.gender}
          onChange={(value) => setFormData({ ...formData, gender: value })}
        />

        <PhoneInput
          value={formData.phone}
          onChange={(value) => setFormData({ ...formData, phone: value })}
          error={errors.phone}
        />

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
