import { createSupabaseServer } from "@/lib/supabase";
import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { getStudentProfile } from "@/actions/student-registration";
import ProfileForm from "./ProfileForm";
import styles from "../join/join.module.css";
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
    <main className={styles.page}>
      <h1 style={{ fontSize: 28, marginBottom: 12 }}>プロフィール</h1>
      <p style={{ marginBottom: 18, color: "#6b7280" }}>
        学生情報が未登録の場合はここで登録・修正してください。
      </p>

      <ProfileForm initial={profile} />
    </main>
  );
}
