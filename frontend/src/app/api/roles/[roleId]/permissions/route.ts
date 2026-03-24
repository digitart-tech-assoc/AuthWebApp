import { NextResponse } from "next/server";

import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { fetchBackend } from "@/lib/backendFetch";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ roleId: string }> }
) {
  try {
    const authorization = await getBackendAuthorizationHeader();
    if (!authorization) {
      return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
    }

    const { roleId } = await params;
    const body = await request.json();
    const res = await fetchBackend(`/api/v1/roles/${roleId}/permissions`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: authorization,
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ ok: false, detail: "permissions proxy failed" }, { status: 502 });
  }
}
