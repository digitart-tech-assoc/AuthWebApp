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
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";
const ROLE_SYNC_INTERVAL_MS = 60 * 1000;

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

async function fetchUserRoleBySub(sub: string): Promise<{ app_role: string; discord_id?: string } | null> {
	if (!sub) {
		return null;
	}
	try {
		const url = `${BACKEND_URL}/api/v1/auth/role-by-sub?sub=${encodeURIComponent(sub)}`;
		const res = await fetch(url, {
			headers: { Authorization: `Bearer ${SHARED_SECRET}` },
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
			const now = Date.now();
			const keycloakSub = account?.provider === "keycloak" ? account.providerAccountId : undefined;
			if (keycloakSub) {
				token.kcSub = keycloakSub;
			}

			if (account?.access_token) {
				// ログイン直後: access_token を保存してバックエンドに問い合わせ
				token.accessToken = account.access_token;

				// バックエンドDBからroleを取得してトークンに埋め込む
				let userInfo = await fetchUserRole(account.access_token);
				if (!userInfo && keycloakSub) {
					userInfo = await fetchUserRoleBySub(keycloakSub);
				}
				token.appRole = userInfo?.app_role ?? "none";
				token.discordId = userInfo?.discord_id ?? null;
				token.isPaid = false; // ログイン時は is_paid を引数から取らず次回pageで確認
				token.roleSyncedAt = now;
				return token;
			}

			// セッション継続中でも一定間隔でroleを再同期する
			const accessToken = typeof token.accessToken === "string" ? token.accessToken : "";
			if (accessToken) {
				const lastSyncedAt = Number(token.roleSyncedAt ?? 0);
				const shouldSyncRole =
					!token.appRole || !Number.isFinite(lastSyncedAt) || now - lastSyncedAt >= ROLE_SYNC_INTERVAL_MS;

				if (shouldSyncRole) {
					let userInfo = await fetchUserRole(accessToken);
					const subForFallback = typeof token.kcSub === "string" ? token.kcSub : undefined;
					if (!userInfo && subForFallback) {
						userInfo = await fetchUserRoleBySub(subForFallback);
					}
					if (userInfo?.app_role) {
						token.appRole = userInfo.app_role;
					}
					token.discordId = userInfo?.discord_id ?? token.discordId ?? null;
					token.roleSyncedAt = now;
				}
			}
			return token;
		},
		async session({ session, token }): Promise<Session> {
			const mutableSession = session as Session & {
				accessToken?: string;
				user: { role?: string; discordId?: string | null; sub?: string };
			};
			if (token.accessToken) {
				mutableSession.accessToken = String(token.accessToken);
			}
			mutableSession.user = {
				...mutableSession.user,
				role: token.appRole ? String(token.appRole) : "none",
				discordId: token.discordId ? String(token.discordId) : null,
				sub: token.kcSub ? String(token.kcSub) : token.sub ? String(token.sub) : undefined,
			};
			return mutableSession;
		},
	},
});