import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createSupabaseServer } from "@/lib/supabase";

export async function GET() {
  const cookieStore = await cookies();
  const cookieList = cookieStore.getAll().map((c) => ({ name: c.name, value: c.value }));

  const supabase = await createSupabaseServer();
  const { data } = await supabase.auth.getSession();

  return NextResponse.json({ cookies: cookieList, session: data?.session ?? null });
}
