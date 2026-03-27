"use client";

import { useState } from "react";
import styles from "./join.module.css";
import StudentNumberInput from "@/components/forms/StudentNumberInput";
import NameInput from "@/components/forms/NameInput";
import FuriganaInput from "@/components/forms/FuriganaInput";
import DepartmentSelect from "@/components/forms/DepartmentSelect";
import GenderSelect from "@/components/forms/GenderSelect";
import PhoneInput from "@/components/forms/PhoneInput";
import { validateFullName, getDepartmentsFromStudentId, validateFurigana } from "../../lib/validation";

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

    // Allow either 7 digits (e.g. 2312345) or 7-char alphanumeric (must include at least one letter)
    if (!formData.student_number.match(/^(?:\d{7}|(?=.*[A-Z])[A-Z0-9]{7})$/i)) {
      newErrors.student_number = "学生番号は7文字で、数字のみまたは英字を含む組合せが有効です（例: 2312345, A123456）";
    }

    // 名前は姓と名の間に半角スペースを含み、ミドルネームも許容する正規表現で検証
    if (!validateFullName(formData.name)) {
      newErrors.name = "姓と名の間に半角スペースを入れてください（ミドルネームも許容）";
    }

    if (!validateFurigana(formData.furigana)) {
      newErrors.furigana = "フリガナはカタカナで、姓と名の間に半角スペースを入れてください";
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
          onChange={(value) => {
            const newData = { ...formData, student_number: value };
            // Auto-assign department(s) based on student ID
            const autoDepts = getDepartmentsFromStudentId(value);
            if (autoDepts) {
              // If only one department, auto-select it
              // If multiple departments, clear selection so user must choose
              newData.department = autoDepts.length === 1 ? autoDepts[0] : "";
            }
            setFormData(newData);
          }}
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
          options={getDepartmentsFromStudentId(formData.student_number) || undefined}
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
