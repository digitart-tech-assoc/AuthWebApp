"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "../join.module.css";
import {
  checkEligibility,
  getStudentProfile,
  type EligibilityCheckResult,
  type StudentProfile,
} from "@/actions/student-registration";
import FormStep1Eligibility from "../form-step-1";
import FormStep2Input from "../form-step-2";
import FormStep3OTP from "../form-step-3";
import FormStep4Complete from "../form-step-4";

type FormStep = 1 | 2 | 3 | 4;

interface FormState {
  student_number: string;
  name: string;
  furigana: string;
  department: string;
  gender: string | null;
  phone: string;
}

export default function JoinFormPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<FormStep>(1);
  const [eligibility, setEligibility] = useState<EligibilityCheckResult | null>(null);
  const [existingProfile, setExistingProfile] = useState<StudentProfile | null>(null);
  const [formData, setFormData] = useState<FormState>({
    student_number: "",
    name: "",
    furigana: "",
    department: "",
    gender: null,
    phone: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize: check eligibility and fetch existing profile
  useEffect(() => {
    async function initialize() {
      try {
        // check Supabase session via debug route
        const res = await fetch("/api/debug/session", { cache: "no-store" });
        if (!res.ok) {
          router.push("/login");
          return;
        }
        const payload = await res.json();
        if (!payload?.session) {
          router.push("/login");
          return;
        }

        // Check eligibility
        const eligResult = await checkEligibility();
        setEligibility(eligResult);

        if (!eligResult.can_register) {
          setError(eligResult.reason);
          setCurrentStep(1);
          setLoading(false);
          return;
        }

        // Try to fetch existing profile
        try {
          const profile = await getStudentProfile();
          if (profile) {
            setExistingProfile(profile);
            setFormData({
              student_number: profile.student_number,
              name: profile.name,
              furigana: profile.furigana,
              department: profile.department,
              gender: profile.gender || null,
              phone: profile.phone,
            });
          }
        } catch {
          // No existing profile, that's fine
        }

        setCurrentStep(2);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "予期しないエラーが発生しました");
        setLoading(false);
      }
    }

    initialize();
  }, [router]);

  const handleStep1Continue = () => {
    if (eligibility?.can_register) {
      setCurrentStep(2);
      setError(null);
    }
  };

  const handleStep2Continue = (newFormData: FormState) => {
    setFormData(newFormData);
    setCurrentStep(3);
    setError(null);
  };

  const handleStep2Back = () => {
    setCurrentStep(1);
  };

  const handleStep3Back = () => {
    setCurrentStep(2);
  };

  const handleStep3Complete = () => {
    setCurrentStep(4);
    setError(null);
  };

  const handleStep4Complete = () => {
    router.push("/roles");
  };

  if (loading) {
    return (
      <main className={styles.page}>
        <div className={styles.hero}>
          <h1 className={styles.title}>本入会フォーム</h1>
          <p>読み込み中...</p>
        </div>
      </main>
    );
  }

  if (error && currentStep === 1) {
    return (
      <main className={styles.page}>
        <div className={styles.hero}>
          <h1 className={styles.title}>入会資格確認</h1>
          <div style={{ color: "#dc2626", marginTop: "16px" }}>
            <p>{error}</p>
            <button
              onClick={() => router.push("/join")}
              style={{
                marginTop: "16px",
                padding: "8px 16px",
                background: "#3b82f6",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              戻る
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <div className={styles.hero}>
        <h1 className={styles.title}>本入会フォーム</h1>
        <p className={styles.lead}>
          ステップ {currentStep} / 4
        </p>
      </div>

      {currentStep === 1 && (
        <FormStep1Eligibility
          eligibility={eligibility}
          onContinue={handleStep1Continue}
        />
      )}

      {currentStep === 2 && (
        <FormStep2Input
          initialData={formData}
          hasExistingProfile={!!existingProfile}
          onContinue={handleStep2Continue}
          onBack={handleStep2Back}
        />
      )}

      {currentStep === 3 && (
        <FormStep3OTP
          studentNumber={formData.student_number}
          name={formData.name}
          onComplete={handleStep3Complete}
          onBack={handleStep3Back}
          formData={formData}
        />
      )}

      {currentStep === 4 && (
        <FormStep4Complete
          studentNumber={formData.student_number}
          name={formData.name}
          onComplete={handleStep4Complete}
        />
      )}

      {error && currentStep > 1 && (
        <div
          style={{
            marginTop: "20px",
            padding: "16px",
            background: "#fee2e2",
            color: "#dc2626",
            borderRadius: "8px",
          }}
        >
          {error}
        </div>
      )}
    </main>
  );
}

