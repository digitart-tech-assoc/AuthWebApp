import NextAuth from "next-auth";
import type { JWT } from "next-auth/jwt";
import type { Session } from "next-auth";
import Keycloak from "next-auth/providers/keycloak";

const keycloakConfigured = Boolean(
	process.env.AUTH_KEYCLOAK_ISSUER?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_ID?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_SECRET?.trim(),
);

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** ログイン後にバックエンドDBからユーザーのapp_roleを取得する */
async function fetchUserRole(accessToken: string): Promise<{ app_role: string; discord_id?: string } | null> {
	try {
		const res = await fetch(`${BACKEND_URL}/api/v1/auth/login-or-register`, {
			method: "POST",
			headers: { Authorization: `Bearer ${accessToken}` },
			cache: "no-store",
		});
		if (!res.ok) {
			return null;
		}
		return await res.json();
	} catch {
		return null;
	}
}

export const { handlers, auth, signIn, signOut } = NextAuth({
	providers: keycloakConfigured
		? [
				Keycloak({
					issuer: process.env.AUTH_KEYCLOAK_ISSUER,
					clientId: process.env.AUTH_KEYCLOAK_CLIENT_ID,
					clientSecret: process.env.AUTH_KEYCLOAK_CLIENT_SECRET,
				}),
			]
		: [],
	session: { strategy: "jwt" },
	trustHost: true,
	callbacks: {
		async jwt({ token, account }): Promise<JWT> {
			if (account?.access_token) {
				// ログイン直後: access_token を保存してバックエンドに問い合わせ
				token.accessToken = account.access_token;

				// バックエンドDBからroleを取得してトークンに埋め込む
				const userInfo = await fetchUserRole(account.access_token);
				token.appRole = userInfo?.app_role ?? "none";
				token.discordId = userInfo?.discord_id ?? null;
				token.isPaid = false; // ログイン時は is_paid を引数から取らず次回pageで確認
			}
			return token;
		},
		async session({ session, token }): Promise<Session> {
			const mutableSession = session as Session & {
				accessToken?: string;
				user: { role?: string; discordId?: string | null };
			};
			if (token.accessToken) {
				mutableSession.accessToken = String(token.accessToken);
			}
			if (token.appRole) {
				mutableSession.user = {
					...mutableSession.user,
					role: String(token.appRole),
					discordId: token.discordId ? String(token.discordId) : null,
				};
			}
			return mutableSession;
		},
	},
});