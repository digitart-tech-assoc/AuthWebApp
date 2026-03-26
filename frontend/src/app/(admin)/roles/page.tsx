// 役割: ロール管理画面

import { createSupabaseServer } from "@/lib/supabase";
import { getBackendAuthorizationHeader } from "@/lib/backendAuth";
import { fetchManifest } from "@/actions/manifest";
import RoleAccordion from "@/components/roles/RoleAccordion";
import { redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function resolveRoleFromBackend(authorization: string): Promise<string> {
	try {
		const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
			headers: { Authorization: authorization },
			cache: "no-store",
		});
		if (res.ok) {
			const data = (await res.json()) as { app_role?: string };
			return data.app_role ?? "none";
		}
	} catch {
		// フォールバック
	}
	return "none";
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
	const supabase = await createSupabaseServer();
	const {
		data: { user },
	} = await supabase.auth.getUser();

	// middleware でルート保護済みだが、念のためSSR側でも確認
	if (!user) {
		redirect("/login?callbackUrl=%2Froles");
	}

	const authorization = await getBackendAuthorizationHeader();
	if (!authorization) {
		redirect("/login?callbackUrl=%2Froles");
	}

	const role = await resolveRoleFromBackend(authorization);
	const isAdmin = role === "admin";

	const displayName =
		user.user_metadata?.full_name ??
		user.user_metadata?.name ??
		user.email ??
		"不明";

	let manifest;
	let accessError: string | null = null;
	try {
		manifest = await fetchManifest();
	} catch (error) {
		if (error instanceof Error && error.message === "unauthorized") {
			redirect("/login?callbackUrl=%2Froles");
		}
		if (error instanceof Error && error.message === "forbidden") {
			accessError =
				"このアカウントは現在メンバー権限として認識されていません。管理者に権限を確認してください。";
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
			<p style={{ marginBottom: 12, color: "#6b7280", fontSize: 14 }}>
				サインイン中: {displayName}（ロール: {role}）{" "}
				<a href="/api/auth/signout?callbackUrl=%2F">ログアウト</a>
			</p>

			{synced && !hasError ? (
				<p style={{ marginTop: 8, color: "#166534" }}>
					同期完了: {syncedRoles} 件のロールを更新しました。
				</p>
			) : null}
			{hasError ? (
				<p style={{ marginTop: 8, color: "#b91c1c" }}>
					同期に失敗しました。しばらくしてから再実行してください。
				</p>
			) : null}
			{pushed && !pushError ? (
				<p style={{ marginTop: 8, color: "#166534" }}>
					push完了: updated={updated}, created={created}, deleted={deleted},
					reordered={reordered}
				</p>
			) : null}
			{pushError ? (
				<p style={{ marginTop: 8, color: "#b91c1c" }}>
					pushに失敗しました。設定と権限を確認してください。
				</p>
			) : null}
			{accessError ? (
				<p style={{ marginTop: 8, color: "#b91c1c" }}>{accessError}</p>
			) : null}

			<RoleAccordion
				categories={manifest.categories}
				roles={manifest.roles}
				accessRole={role}
			/>
		</main>
	);
}
