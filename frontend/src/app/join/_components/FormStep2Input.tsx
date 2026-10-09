"use client";

import StudentProfileForm from "@/components/forms/StudentProfileForm";
import { alertInfo, card, cardTitle } from "./joinStyles";
import type { StudentProfileInput } from "@/types/join";

interface FormStep2Props {
  initialData: StudentProfileInput;
  hasExistingProfile: boolean;
  onContinue: (data: StudentProfileInput) => void;
  onBack: () => void;
}

export default function FormStep2Input({
  initialData,
  hasExistingProfile,
  onContinue,
  onBack,
}: FormStep2Props) {
  const handleSubmit = async (data: StudentProfileInput) => {
    onContinue(data);
  };

  return (
    <div className={card}>
      <h2 className={cardTitle}>個人情報入力</h2>

      {hasExistingProfile && (
        <div className={`${alertInfo} mb-4`}>
          💡 Pre-member として登録済みの情報を自動入力しました。変更があれば編集してください。
        </div>
      )}

      <StudentProfileForm initialData={initialData} hasExistingProfile={hasExistingProfile} onSubmit={handleSubmit} onBack={onBack} submitLabel={"続行 →"} />
    </div>
  );
}
