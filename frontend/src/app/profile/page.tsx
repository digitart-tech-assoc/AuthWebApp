import { createSupabaseServer } from "@/lib/supabase";
import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { getStudentProfile } from "@/actions/studentRegistration";
import ProfileForm from "./_components/ProfileForm";
import { redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function resolveRoleFromBackend(authorization: string): Promise<string> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
      headers: { Authorization: authorization },
      cache: "no-store",
    });
    if (res.ok) {
      const data = (await res.json()) as { app_role?: string };
      return data.app_role ?? "none";
    }
  } catch {
    // fallback
  }
  return "none";
}

export default async function ProfilePage() {
  const supabase = await createSupabaseServer();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect(`/login?callbackUrl=%2Fprofile`);
  }

  const authorization = await getBackendAuthorizationHeader();
  if (!authorization) {
    redirect(`/login?callbackUrl=%2Fprofile`);
  }

  const role = await resolveRoleFromBackend(authorization);
  const isMember = role === "member" || role === "admin" || role === "obog";
  if (!isMember) {
    // not allowed
    redirect(`/login?callbackUrl=%2Fprofile`);
  }

  // Fetch existing profile (may be null)
  const profile = await getStudentProfile();

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 pb-16 sm:py-12 sm:pb-20">
      <h1 className="mb-3 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">プロフィール</h1>
      <p className="mb-5 text-sm leading-relaxed text-slate-500 sm:text-base">
        学生情報が未登録の場合はここで登録・修正してください。
      </p>

      <ProfileForm initial={profile} />
    </main>
  );
}
