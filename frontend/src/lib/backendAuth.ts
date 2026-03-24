import "server-only";

import { auth } from "@/auth";

const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";
const KEYCLOAK_CONFIGURED = Boolean(
	process.env.AUTH_KEYCLOAK_ISSUER?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_ID?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_SECRET?.trim(),
);
const AUTH_REQUIRED = process.env.AUTH_REQUIRED !== "false" && KEYCLOAK_CONFIGURED;

export async function getBackendAuthorizationHeader(): Promise<string | null> {
	const session = (await auth()) as { accessToken?: string } | null;
	const accessToken = session?.accessToken?.trim();

	if (accessToken) {
		return `Bearer ${accessToken}`;
	}

	if (!AUTH_REQUIRED) {
		return `Bearer ${SHARED_SECRET}`;
	}

	return null;
}