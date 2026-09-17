import { NextResponse } from "next/server";

import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";
import { createSupabaseServer } from "@/lib/supabase";
import { cookies } from "next/headers";

export async function POST(request: Request) {
  try {
    const authorization = await getBackendAuthorizationHeader();
    if (!authorization) {
      // Helpful debug info during development to diagnose missing session/discord link.
      if (process.env.NODE_ENV !== "production") {
        const cookieStore = await cookies();
        const cookieList = cookieStore.getAll().map((c) => ({ name: c.name, value: c.value }));
        const supabase = await createSupabaseServer();
        const { data } = await supabase.auth.getSession();
        const sessionExists = !!data?.session;
        const providerId = data?.session?.user?.user_metadata?.provider_id ?? null;
        return NextResponse.json(
          {
            ok: false,
            detail: "Unauthorized",
            debug: { sessionExists, providerId, cookies: cookieList.map((c) => c.name) },
          },
          { status: 401 },
        );
      }

      return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
    }

    const payload = await request.json();
    const res = await fetchBackend("/api/v1/survey", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authorization,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const body = await res.json().catch(() => ({}));
    return NextResponse.json(body, { status: res.status });
  } catch {
    return NextResponse.json({ ok: false, detail: "survey proxy failed" }, { status: 502 });
  }
}
