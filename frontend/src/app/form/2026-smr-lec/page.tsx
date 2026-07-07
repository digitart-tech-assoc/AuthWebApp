import type { Metadata } from "next";
import { createSupabaseServer } from "@/lib/supabase";
import LectureFormPage from "./LectureFormPage";
import { UserInfo } from "@/lib/lectureTypes";

export const metadata: Metadata = {
  title: "講座申し込みフォーム | 2026 Summer Lecture Series",
  description:
    "サークルの2026年夏の講座（8月1日〜9月13日）を申し込むためのフォームです。希望の時間帯をカレンダーで選択して申し込んでください。",
};

/** Discord provider_id → user_memberships を突き合わせてAdmin判定 */
async function checkAdminStatus(discordId: string | null): Promise<boolean> {
  if (!discordId) return false;
  try {
    // Service Role クライアントを使用（RLS バイパス）
    const { createClient } = await import("@supabase/supabase-js");
    const serviceClient = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );
    const { data, error } = await serviceClient
      .from("user_memberships")
      .select("id")
      .eq("discord_id", discordId)
      .eq("membership_type", "admin")
      .maybeSingle();
    return !error && data !== null;
  } catch {
    return false;
  }
}

export default async function Page() {
  let userInfo: UserInfo | null = null;

  try {
    const supabase = await createSupabaseServer();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (user) {
      // Discord provider_id (Discord User ID)
      const discordId =
        user.user_metadata?.provider_id ??
        user.user_metadata?.sub ??
        null;

      // Discord名: full_name → custom_claims.global_name → email
      const discordName =
        user.user_metadata?.full_name ??
        user.user_metadata?.name ??
        user.user_metadata?.global_name ??
        user.email ??
        null;

      const isAdmin = await checkAdminStatus(discordId);

      userInfo = {
        id: user.id,
        discordName,
        discordId,
        isAdmin,
      };
    }
  } catch (error) {
    console.error("Error fetching user in lecture form page:", error);
  }

  return <LectureFormPage userInfo={userInfo} />;
}
