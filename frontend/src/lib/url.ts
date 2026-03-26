import type { NextRequest } from "next/server";

export function getBaseUrl(request: NextRequest) {
  const origin = new URL(request.url).origin;
  const envBase = process.env.NEXT_PUBLIC_SITE_URL ?? process.env.FRONTEND_ORIGIN ?? origin;
  // replace host 0.0.0.0 with localhost when present
  const normalized = envBase.replace("0.0.0.0", "localhost");
  return normalized.replace(/\/+$/, "");
}
