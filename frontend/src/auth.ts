import NextAuth from "next-auth";
import type { Session } from "next-auth";
import Keycloak from "next-auth/providers/keycloak";

const keycloakConfigured = Boolean(
	process.env.AUTH_KEYCLOAK_ISSUER?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_ID?.trim() &&
		process.env.AUTH_KEYCLOAK_CLIENT_SECRET?.trim(),
);

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
		async jwt({ token, account }) {
			if (account?.access_token) {
				token.accessToken = account.access_token;
			}
			return token;
		},
		async session({ session, token }) {
			const mutableSession = session as Session & { accessToken?: string };
			if (token.accessToken) {
				mutableSession.accessToken = String(token.accessToken);
			}
			return mutableSession;
		},
	},
});