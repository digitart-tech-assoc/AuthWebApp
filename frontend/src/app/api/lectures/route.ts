import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { LectureInsert } from "@/lib/lectureTypes";

/** Service Role を使うサーバー専用クライアント（RLS をバイパスして管理者操作に使用） */
function createServiceClient() {
  const { createClient } = require("@supabase/supabase-js");
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

/** Cookie ベースのクライアント（通常ユーザー操作） */
async function createAuthClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Server Component の場合は無視
          }
        },
      },
    }
  );
}

/** ユーザーが Admin かどうか判定 */
async function isAdmin(discordId: string | null): Promise<boolean> {
  if (!discordId) return false;
  const service = createServiceClient();
  const { data, error } = await service
    .from("user_memberships")
    .select("id")
    .eq("discord_id", discordId)
    .eq("membership_type", "admin")
    .maybeSingle();
  return !error && data !== null;
}

// ============================================================
// GET /api/lectures
// ============================================================
export async function GET() {
  try {
    const supabase = await createAuthClient();
    const { data, error } = await supabase
      .from("lectures")
      .select("*")
      .gte("start_at", "2026-08-01T00:00:00+09:00")
      .lte("end_at", "2026-09-14T00:00:00+09:00")
      .order("start_at", { ascending: true });

    if (error) throw error;
    return NextResponse.json({ lectures: data ?? [] });
  } catch (err) {
    console.error("GET /api/lectures error:", err);
    return NextResponse.json({ error: "Failed to fetch lectures" }, { status: 500 });
  }
}

// ============================================================
// POST /api/lectures
// ============================================================
export async function POST(req: NextRequest) {
  try {
    const body: LectureInsert = await req.json();

    // バリデーション
    if (!body.title?.trim()) {
      return NextResponse.json({ error: "講座タイトルは必須です" }, { status: 400 });
    }
    if (!body.discord_name?.trim()) {
      return NextResponse.json({ error: "Discord名は必須です" }, { status: 400 });
    }
    if (!body.start_at || !body.end_at) {
      return NextResponse.json({ error: "開始・終了日時は必須です" }, { status: 400 });
    }
    const startDate = new Date(body.start_at);
    const endDate = new Date(body.end_at);
    if (startDate >= endDate) {
      return NextResponse.json({ error: "終了時刻は開始時刻より後にしてください" }, { status: 400 });
    }

    // ログイン状態を確認
    const supabase = await createAuthClient();
    const { data: { user } } = await supabase.auth.getUser();

    const payload: LectureInsert = {
      title: body.title.trim(),
      start_at: body.start_at,
      end_at: body.end_at,
      discord_name: body.discord_name.trim(),
      notes: body.notes?.trim() || null,
      is_authenticated_booking: !!user,
      user_id: user?.id ?? null,
    };

    // Service Role で挿入（anon policy も insert を許可しているが一貫性のため）
    const service = createServiceClient();
    const { data, error } = await service
      .from("lectures")
      .insert(payload)
      .select()
      .single();

    if (error) {
      if (error.message?.includes("lectures_no_overlap")) {
        return NextResponse.json(
          { error: "選択した時間帯はすでに予約されています。別の時間帯をお選びください。" },
          { status: 409 }
        );
      }
      if (error.message?.includes("lectures_in_period")) {
        return NextResponse.json(
          { error: "申し込み期間（8月1日〜9月13日）内の時間帯を選択してください。" },
          { status: 400 }
        );
      }
      throw error;
    }

    return NextResponse.json({ lecture: data }, { status: 201 });
  } catch (err) {
    console.error("POST /api/lectures error:", err);
    return NextResponse.json({ error: "申し込みに失敗しました。時間をおいて再度お試しください。" }, { status: 500 });
  }
}
