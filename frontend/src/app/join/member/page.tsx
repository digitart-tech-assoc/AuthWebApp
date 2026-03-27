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

export default function JoinMemberPage() {
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

  useEffect(() => {
    async function initialize() {
      try {
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

        const eligResult = await checkEligibility();
        setEligibility(eligResult);

        // Do not early-return on not-allowed; allow the eligibility component
        // to show detailed guidance (e.g. redirect to provisional form or contact).
        if (!eligResult.can_register) {
          setCurrentStep(1);
          setLoading(false);
          // keep `eligibility` populated and avoid setting `error` so the
          // `FormStep1Eligibility` component can render helpful guidance.
        } else {
          // allowed to proceed: fetch profile and continue
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
            // ignore
          }

          setCurrentStep(2);
          setLoading(false);
        }

        // (profile fetching and step advancement handled above when allowed)
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

  const handleStep2Back = () => setCurrentStep(1);
  const handleStep3Back = () => setCurrentStep(2);
  const handleStep3Complete = () => { setCurrentStep(4); setError(null); };
  const handleStep4Complete = () => router.push("/roles");

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

  // Do not short-circuit on `eligibility` failures; show FormStep1Eligibility instead.

  return (
    <main className={styles.page}>
      <div className={styles.hero}>
        <h1 className={styles.title}>本入会フォーム</h1>
        <p className={styles.lead}>ステップ {currentStep} / 4</p>
      </div>

      {currentStep === 1 && (
        <FormStep1Eligibility eligibility={eligibility} onContinue={handleStep1Continue} />
      )}

      {currentStep === 2 && (
        <FormStep2Input initialData={formData} hasExistingProfile={!!existingProfile} onContinue={handleStep2Continue} onBack={handleStep2Back} />
      )}

      {currentStep === 3 && (
        <FormStep3OTP studentNumber={formData.student_number} name={formData.name} onComplete={handleStep3Complete} onBack={handleStep3Back} formData={formData} />
      )}

      {currentStep === 4 && (
        <FormStep4Complete studentNumber={formData.student_number} name={formData.name} onComplete={handleStep4Complete} />
      )}

      {error && currentStep > 1 && (
        <div style={{ marginTop: 20, padding: 16, background: "#fee2e2", color: "#dc2626", borderRadius: 8 }}>{error}</div>
      )}
    </main>
  );
}
