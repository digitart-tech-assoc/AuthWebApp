"use client";

import StudentProfileForm from "@/components/forms/StudentProfileForm";
import styles from "../join/join.module.css";
import { submitStudentProfile, type StudentProfile } from "@/actions/student-registration";

interface Props {
  initial?: StudentProfile | null;
}

export default function ProfileForm({ initial }: Props) {
  const handleSubmit = async (data: StudentProfile) => {
    await submitStudentProfile(data);
  };

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>個人情報入力</h2>

      <StudentProfileForm initialData={initial ?? null} hasExistingProfile={!!initial} onSubmit={handleSubmit} />
    </div>
  );
}
