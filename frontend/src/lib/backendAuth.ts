import "server-only";

import { auth } from "@/auth";

const KEYCLOAK_CONFIGURED = Boolean(
	process.env.AUTH_KEYCLOAK_ISSUER?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_ID?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_SECRET?.trim(),
);
const AUTH_REQUIRED = process.env.AUTH_REQUIRED !== "false" && KEYCLOAK_CONFIGURED;
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

type SessionWithToken = {
	accessToken?: string;
	user?: { role?: string; discordId?: string | null };
} | null;

export async function getBackendAuthorizationHeader(): Promise<string | null> {
	const session = (await auth()) as SessionWithToken;
	const accessToken = session?.accessToken?.trim();

	if (accessToken) {
		return `Bearer ${accessToken}`;
	}

	if (!AUTH_REQUIRED) {
		return `Bearer ${SHARED_SECRET}`;
	}

	return null;
}

/** セッションからアプリロールを取得する */
export async function getSessionRole(): Promise<string> {
	const session = (await auth()) as SessionWithToken;
	return session?.user?.role ?? "none";
}