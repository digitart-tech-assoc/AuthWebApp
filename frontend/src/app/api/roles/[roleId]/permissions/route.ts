// 役割: ロール権限即時更新プロキシ

import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ roleId: string }> }
) {
  const { roleId } = await params;
  const body = await request.json();
  const res = await fetch(
    `${BACKEND_URL}/api/v1/roles/${roleId}/permissions`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${SHARED_SECRET}`,
      },
      body: JSON.stringify(body),
    }
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
