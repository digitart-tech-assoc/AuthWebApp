import "server-only";
import { headers } from "next/headers";

/**
 * Server Action から Backend を呼ぶときに付けるヘッダー。
 * Backend からは接続元が Frontend になるため、受け取った X-Forwarded-For（ingress が付けたクライアント IP）を
 * そのまま転送し、Backend の IP 単位のレート制限に使わせる。
 */
export async function getForwardedForHeader(): Promise<Record<string, string>> {
	const forwardedFor = (await headers()).get("x-forwarded-for");
	return forwardedFor ? { "X-Forwarded-For": forwardedFor } : {};
}
