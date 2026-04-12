"use client";

import { useState } from "react";
import styles from "@/app/join/join.module.css";
import StudentNumberInput from "@/components/forms/StudentNumberInput";
import NameInput from "@/components/forms/NameInput";
import FuriganaInput from "@/components/forms/FuriganaInput";
import DepartmentSelect from "@/components/forms/DepartmentSelect";
import GenderSelect from "@/components/forms/GenderSelect";
import PhoneInput from "@/components/forms/PhoneInput";
import { validateFullName, getDepartmentsFromStudentId, validateFurigana } from "@/lib/validation";
import type { StudentProfile } from "@/actions/student-registration";

interface Props {
  // Accept partial so caller doesn't need to include backend-only fields like `email_aoyama`.
  initialData?: Partial<StudentProfile> | null;
  hasExistingProfile?: boolean;
  onSubmit: (data: StudentProfile) => Promise<void> | void;
  onBack?: () => void;
  submitLabel?: string;
}

export default function StudentProfileForm({ initialData, hasExistingProfile, onSubmit, onBack, submitLabel = "保存" }: Props) {
  const [formData, setFormData] = useState<StudentProfile>({
    student_number: initialData?.student_number ?? "",
    name: initialData?.name ?? "",
    furigana: initialData?.furigana ?? "",
    department: initialData?.department ?? "",
    gender: (initialData?.gender as string) ?? null,
    phone: initialData?.phone ?? "",
    // email_aoyama is populated by OTP send response; default to empty string here.
    email_aoyama: (initialData as any)?.email_aoyama ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.student_number.match(/^(?:\d{8}|(?=.*[A-Z])[A-Z0-9]{7})$/i)) {
      newErrors.student_number = "学生番号は8文字で有効な形式を入力してください";
    }

    if (!validateFullName(formData.name)) {
      newErrors.name = "姓と名の間に半角スペースを入れてください";
    }

    if (!validateFurigana(formData.furigana)) {
      newErrors.furigana = "フリガナはカタカナで、姓と名の間に半角スペースを入れてください";
    }

    if (formData.department.trim().length === 0) {
      newErrors.department = "学部学科を選択してください";
    }

    if (!formData.phone.match(/^\d{10,11}$/)) {
      newErrors.phone = "電話番号は10〜11桁の数字で入力してください";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!validate()) return;
    try {
      setLoading(true);
      setMessage(null);
      await onSubmit(formData);
      setMessage("保存しました");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} style={{ marginTop: 16 }}>
        <StudentNumberInput
          value={formData.student_number}
          onChange={(value) => {
            const newData = { ...formData, student_number: value };
            const autoDepts = getDepartmentsFromStudentId(value);
            if (autoDepts) {
              newData.department = autoDepts.length === 1 ? autoDepts[0] : newData.department;
            }
            setFormData(newData);
          }}
          error={errors.student_number}
        />

        <NameInput value={formData.name} onChange={(v) => setFormData({ ...formData, name: v })} error={errors.name} />

        <FuriganaInput value={formData.furigana} onChange={(v) => setFormData({ ...formData, furigana: v })} error={errors.furigana} />

        <DepartmentSelect
          value={formData.department}
          onChange={(v) => setFormData({ ...formData, department: v })}
          options={getDepartmentsFromStudentId(formData.student_number) || undefined}
          error={errors.department}
        />

        <GenderSelect value={formData.gender} onChange={(v) => setFormData({ ...formData, gender: v })} />

        <PhoneInput value={formData.phone} onChange={(v) => setFormData({ ...formData, phone: v })} error={errors.phone} />

        <div style={{ display: "flex", gap: 12, justifyContent: "space-between", marginTop: 12 }}>
          <div />
          <div style={{ display: "flex", gap: 12 }}>
            {onBack && (
              <button type="button" onClick={onBack} className={styles.secondary} disabled={loading}>
                ← 戻る
              </button>
            )}
            <button type="submit" className={styles.primary} disabled={loading}>
              {loading ? "保存中..." : submitLabel}
            </button>
          </div>
        </div>
      </form>

      {message && <div style={{ marginTop: 12, color: message.includes("失敗") ? "#b91c1c" : "#065f46" }}>{message}</div>}
    </>
  );
}
