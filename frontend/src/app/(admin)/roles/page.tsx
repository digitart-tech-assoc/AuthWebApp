// 役割: ロール管理画面（member/admin でUI差分制御）

import { auth } from "@/auth";
import { fetchManifest } from "@/actions/manifest";
import RoleAccordion from "@/components/roles/RoleAccordion";
import { redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

async function resolveRoleFromBackend(
	accessToken: string | undefined,
	sub: string | undefined,
	fallbackRole: string,
): Promise<string> {
	if (accessToken) {
		try {
			const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
				headers: { Authorization: `Bearer ${accessToken}` },
				cache: "no-store",
			});
			if (res.ok) {
				const data = (await res.json()) as { app_role?: string };
				return data.app_role ?? fallbackRole;
			}
		} catch {
			// フォールバックへ
		}
	}

	try {
		if (!sub) {
			return fallbackRole;
		}
		const url = `${BACKEND_URL}/api/v1/auth/role-by-sub?sub=${encodeURIComponent(sub)}`;
		const res = await fetch(url, {
			headers: { Authorization: `Bearer ${SHARED_SECRET}` },
			cache: "no-store",
		});
		if (!res.ok) {
			return fallbackRole;
		}
		const data = (await res.json()) as { app_role?: string };
		return data.app_role ?? fallbackRole;
	} catch {
		return fallbackRole;
	}
}

type SearchParamsType = {
	synced?: string;
	roles?: string;
	error?: string;
	pushed?: string;
	push_error?: string;
	updated?: string;
	created?: string;
	deleted?: string;
	reordered?: string;
};

type RolesPageProps = {
	searchParams?: SearchParamsType | Promise<SearchParamsType>;
};

export default async function RolesPage({ searchParams }: RolesPageProps) {
	const session = await auth();
	const sessionWithRole = session as typeof session & {
		accessToken?: string;
		user?: { role?: string; discordId?: string | null; sub?: string };
	};

	// middleware でルート保護済みだが、念のためSSR側でも確認
	if (!session?.user) {
		redirect("/api/auth/signin?callbackUrl=%2Froles");
	}

	const fallbackRole = sessionWithRole?.user?.role ?? "none";
	const role = await resolveRoleFromBackend(sessionWithRole?.accessToken, sessionWithRole?.user?.sub, fallbackRole);
	const isAdmin = role === "admin";

	let manifest;
	let accessError: string | null = null;
	try {
		manifest = await fetchManifest();
	} catch (error) {
		if (error instanceof Error && (error.message === "unauthorized" || error.message.includes("manifest fetch failed"))) {
			redirect("/api/auth/signin?callbackUrl=%2Froles");
		}
		if (error instanceof Error && error.message === "forbidden") {
			accessError = "このアカウントは現在メンバー権限として認識されていません。管理者に権限を確認してください。";
			manifest = { categories: [], roles: [] };
		} else {
			throw error;
		}
	}

	const params = await Promise.resolve(searchParams);
	const synced = params?.synced === "1";
	const hasError = params?.error === "1";
	const syncedRoles = Number(params?.roles ?? "0");
	const pushed = params?.pushed === "1";
	const pushError = params?.push_error === "1";
	const updated = Number(params?.updated ?? "0");
	const created = Number(params?.created ?? "0");
	const deleted = Number(params?.deleted ?? "0");
	const reordered = Number(params?.reordered ?? "0");

	return (
		<main style={{ padding: 24 }}>
			<h1>ロール管理</h1>
			<p>Discordから取得して保存したロールを表示します。</p>

			{session?.user ? (
				<p style={{ marginBottom: 12, color: "#6b7280", fontSize: 14 }}>
					サインイン中: {session.user.name ?? session.user.email ?? sessionWithRole.user?.discordId ?? "不明"}
					{" "}（ロール: {role}）
					{" "}<a href="/api/auth/signout?callbackUrl=%2F">ログアウト</a>
				</p>
			) : null}

			{/* Admin専用操作エリア */}
			{isAdmin ? (
				<div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
					<SyncButton />
					<PushButton />
				</div>
			) : (
				<p style={{ fontSize: 13, color: "#9ca3af", marginBottom: 16 }}>
					ロールの同期・適用操作はAdminのみ実行できます。
				</p>
			)}

			{synced && !hasError ? (
				<p style={{ marginTop: 8, color: "#166534" }}>同期完了: {syncedRoles} 件のロールを更新しました。</p>
			) : null}
			{hasError ? (
				<p style={{ marginTop: 8, color: "#b91c1c" }}>同期に失敗しました。しばらくしてから再実行してください。</p>
			) : null}
			{pushed && !pushError ? (
				<p style={{ marginTop: 8, color: "#166534" }}>
					push完了: updated={updated}, created={created}, deleted={deleted}, reordered={reordered}
				</p>
			) : null}
			{pushError ? (
				<p style={{ marginTop: 8, color: "#b91c1c" }}>pushに失敗しました。設定と権限を確認してください。</p>
			) : null}

			{accessError ? (
				<p style={{ marginTop: 8, color: "#b91c1c" }}>{accessError}</p>
			) : null}

			<RoleAccordion
				categories={manifest.categories}
				roles={manifest.roles}
			/>
		</main>
	);
}
