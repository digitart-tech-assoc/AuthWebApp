"use client";

import { useEffect, useState } from "react";
import { Check, AlertCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  checkEligibility,
  getStudentProfile,
  type EligibilityCheckResult,
  type StudentProfile,
} from "@/actions/student-registration";
import FormStep1Eligibility from "../form-step-1";
import FormStep2Input from "../form-step-2";
import FormStep3Survey from "../form-step-3";
import FormStep4OTP from "../form-step-4";
import FormStep5Complete from "../form-step-5";
import { fetchBackend } from "@/lib/backendFetch";

type FormStep = 1 | 2 | 3 | 4 | 5;

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
        if (err instanceof Error && err.message === "Not authenticated") {
          router.push("/login");
          return;
        }
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
  const persistSurvey = async (answers?: any) => {
    try {
      const res = await fetch('/api/survey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(answers || {}),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || res.statusText || 'Failed to save survey');
      }
      return await res.json();
    } catch (err) {
      throw err;
    }
  };

  const handleStep3Complete = async (answers?: any) => {
    setError(null);
    try {
      await persistSurvey(answers);
      setCurrentStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save survey');
    }
  };
  const handleStep4Back = () => setCurrentStep(3);
  const handleStep4Complete = () => { setCurrentStep(5); setError(null); };
  const handleStep5Complete = () => router.push("/roles");

  if (loading) {
    return (
      <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
        <section className="bg-gradient-to-br from-slate-50 via-white to-emerald-50 pt-20 pb-16 px-6">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4">本入会フォーム</h1>
            <p className="text-lg text-slate-600">読み込み中...</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
      {/* ヒーロー部分 */}
      <section className="bg-gradient-to-br from-slate-50 via-white to-emerald-50 pt-20 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between gap-4 mb-6">
            <div>
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-2">本入会フォーム</h1>
              <p className="text-lg text-slate-600">ステップ <span className="font-bold text-emerald-600">{currentStep}</span> / 5</p>
            </div>
            {/* プログレスバー */}
            <div className="hidden md:block">
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((step) => (
                  <div
                    key={step}
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                      step < currentStep
                        ? "bg-emerald-600 text-white"
                        : step === currentStep
                        ? "bg-emerald-100 text-emerald-700 ring-2 ring-emerald-500"
                        : "bg-slate-200 text-slate-600"
                    }`}
                  >
                      {step < currentStep ? (
                      <Check className="w-6 h-6" />
                    ) : (
                      step
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* メインコンテンツ */}
      <section className="py-12 md:py-16 px-6">
        <div className="max-w-4xl mx-auto">
          {currentStep === 1 && (
            <FormStep1Eligibility eligibility={eligibility} onContinue={handleStep1Continue} />
          )}

          {currentStep === 2 && (
            <FormStep2Input initialData={formData} hasExistingProfile={!!existingProfile} onContinue={handleStep2Continue} onBack={handleStep2Back} />
          )}

          {currentStep === 3 && (
            <FormStep3Survey onComplete={handleStep3Complete} onBack={handleStep3Back} />
          )}

          {currentStep === 4 && (
            <FormStep4OTP studentNumber={formData.student_number} name={formData.name} onComplete={handleStep4Complete} onBack={handleStep4Back} formData={formData} />
          )}

          {currentStep === 5 && (
            <FormStep5Complete studentNumber={formData.student_number} name={formData.name} onComplete={handleStep5Complete} />
          )}

          {error && currentStep > 1 && (
            <div className="mt-8 bg-red-50 border border-red-200 rounded-lg p-6 flex gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0" />
              <p className="text-red-700 font-medium">{error}</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
