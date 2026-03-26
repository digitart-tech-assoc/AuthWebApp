import "server-only";
import { createSupabaseServer } from "./supabase";

const AUTH_REQUIRED = process.env.AUTH_REQUIRED !== "false";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function getBackendAuthorizationHeader(): Promise<string | null> {
	const supabase = await createSupabaseServer();
	const {
		data: { session },
	} = await supabase.auth.getSession();
	const accessToken = session?.access_token?.trim();

	if (accessToken) {
		return `Bearer ${accessToken}`;
	}

	try {
		const {
			data: { session: refreshedSession },
		} = await supabase.auth.refreshSession();
		const refreshedToken = refreshedSession?.access_token?.trim();
		if (refreshedToken) {
			return `Bearer ${refreshedToken}`;
		}
	} catch {
		// refresh 失敗時は通常のフォールバックへ
	}

	if (!AUTH_REQUIRED) {
		return `Bearer ${SHARED_SECRET}`;
	}

	return null;
}

/** バックエンドの /auth/me を呼んでアプリロールを取得する。
 * バックエンドが 401 を返した場合は login redirectさせるため、ここでは raise する。
 */
export async function getSessionRole(): Promise<string> {
	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		throw new Error("unauthorized");
	}

	const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
		headers: { Authorization: authorization },
		cache: "no-store",
	});

	if (res.status === 401 || res.status === 403) {
		throw new Error(`auth-error-${res.status}`);
	}

	if (res.ok) {
		const data = (await res.json()) as { app_role?: string };
		return data.app_role ?? "none";
	}

	throw new Error(`auth-error-${res.status}`);
}