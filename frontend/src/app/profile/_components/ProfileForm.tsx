"use client";

import StudentProfileForm from "@/components/forms/StudentProfileForm";
import { submitStudentProfile } from "@/actions/studentRegistration";
import { DisplayableError } from "@/lib/errorMessages";
import type { StudentProfile } from "@/types/join";

interface Props {
  initial?: StudentProfile | null;
}

export default function ProfileForm({ initial }: Props) {
  const handleSubmit = async (data: StudentProfile) => {
    const result = await submitStudentProfile(data);
    if (!result.ok) {
      throw new DisplayableError(result.error);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
      <h2 className="mb-2 text-base font-semibold text-slate-900">個人情報入力</h2>

      <StudentProfileForm initialData={initial ?? null} hasExistingProfile={!!initial} onSubmit={handleSubmit} />
    </div>
  );
}
