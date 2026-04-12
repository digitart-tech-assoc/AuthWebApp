"use client";

import StudentProfileForm from "@/components/forms/StudentProfileForm";
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

export default function FormStep2Input({
  initialData,
  hasExistingProfile,
  onContinue,
  onBack,
}: FormStep2Props) {
  const handleSubmit = async (data: FormData) => {
    onContinue(data);
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

      <StudentProfileForm initialData={initialData} hasExistingProfile={hasExistingProfile} onSubmit={handleSubmit} onBack={onBack} submitLabel={"続行 →"} />
    </div>
  );
}
