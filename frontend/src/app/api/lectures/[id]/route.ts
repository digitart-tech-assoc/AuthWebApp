import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { LectureUpdate } from "@/lib/lectureTypes";

function createServiceClient() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createClient } = require("@supabase/supabase-js");
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

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
          } catch { /* ignore */ }
        },
      },
    }
  );
}

async function getAdminStatus(discordId: string | null): Promise<boolean> {
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
// PUT /api/lectures/[id]
// ============================================================
export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body: LectureUpdate = await req.json();

    const supabase = await createAuthClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: "講座の編集にはログインが必要です" }, { status: 401 });
    }

    const service = createServiceClient();

    // 対象講座の取得
    const { data: lecture, error: fetchError } = await service
      .from("lectures")
      .select("*")
      .eq("id", id)
      .single();

    if (fetchError || !lecture) {
      return NextResponse.json({ error: "講座が見つかりません" }, { status: 404 });
    }

    // 権限チェック: 本人 or Admin
    const discordId = user.user_metadata?.provider_id ?? user.user_metadata?.sub ?? null;
    const adminOk = await getAdminStatus(discordId);
    const isOwner = lecture.user_id === user.id;

    if (!isOwner && !adminOk) {
      return NextResponse.json({ error: "この講座を編集する権限がありません" }, { status: 403 });
    }

    // バリデーション
    if (body.start_at && body.end_at) {
      if (new Date(body.start_at) >= new Date(body.end_at)) {
        return NextResponse.json({ error: "終了時刻は開始時刻より後にしてください" }, { status: 400 });
      }
    }

    const { data, error } = await service
      .from("lectures")
      .update({
        ...(body.title && { title: body.title.trim() }),
        ...(body.start_at && { start_at: body.start_at }),
        ...(body.end_at && { end_at: body.end_at }),
        ...(body.discord_name && { discord_name: body.discord_name.trim() }),
        ...(body.notes !== undefined && { notes: body.notes?.trim() || null }),
      })
      .eq("id", id)
      .select()
      .single();

    if (error) {
      if (error.message?.includes("lectures_no_overlap")) {
        return NextResponse.json(
          { error: "選択した時間帯はすでに予約されています。別の時間帯をお選びください。" },
          { status: 409 }
        );
      }
      throw error;
    }

    return NextResponse.json({ lecture: data });
  } catch (err) {
    console.error("PUT /api/lectures/[id] error:", err);
    return NextResponse.json({ error: "更新に失敗しました" }, { status: 500 });
  }
}

// ============================================================
// DELETE /api/lectures/[id]
// ============================================================
export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const supabase = await createAuthClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: "削除にはログインが必要です" }, { status: 401 });
    }

    const service = createServiceClient();

    // 対象講座の取得
    const { data: lecture, error: fetchError } = await service
      .from("lectures")
      .select("*")
      .eq("id", id)
      .single();

    if (fetchError || !lecture) {
      return NextResponse.json({ error: "講座が見つかりません" }, { status: 404 });
    }

    // 権限チェック
    const discordId = user.user_metadata?.provider_id ?? user.user_metadata?.sub ?? null;
    const adminOk = await getAdminStatus(discordId);
    const isOwner = lecture.user_id === user.id;

    if (!isOwner && !adminOk) {
      return NextResponse.json({ error: "この講座を削除する権限がありません" }, { status: 403 });
    }

    const { error } = await service
      .from("lectures")
      .delete()
      .eq("id", id);

    if (error) throw error;

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("DELETE /api/lectures/[id] error:", err);
    return NextResponse.json({ error: "削除に失敗しました" }, { status: 500 });
  }
}
