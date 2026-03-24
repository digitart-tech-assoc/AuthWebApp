// 役割: ロール管理画面

import { fetchManifest } from "@/actions/manifest";
import { triggerSync } from "@/actions/sync";
import RoleAccordion from "@/components/roles/RoleAccordion";
import { redirect } from "next/navigation";

async function SyncButton() {
	async function runSync() {
		"use server";
		let roles = 0;
		try {
			const result = await triggerSync();
			roles = result.roles ?? 0;
		} catch {
			redirect("/roles?error=1");
		}
		redirect(`/roles?synced=1&roles=${roles}`);
	}

	return (
		<form action={runSync}>
			<button type="submit">同期を実行</button>
		</form>
	);
}

type RolesPageProps = {
	searchParams?:
		| {
			synced?: string;
			roles?: string;
			error?: string;
		  }
		| Promise<{
		synced?: string;
		roles?: string;
		error?: string;
	  }>;
};

export default async function RolesPage({ searchParams }: RolesPageProps) {
	const manifest = await fetchManifest();
	const params = await Promise.resolve(searchParams);
	const synced = params?.synced === "1";
	const hasError = params?.error === "1";
	const syncedRoles = Number(params?.roles ?? "0");

	return (
		<main style={{ padding: 24 }}>
			<h1>ロール管理</h1>
			<p>Discordから取得して保存したロールを表示します。</p>
			<SyncButton />
			{synced && !hasError ? (
				<p style={{ marginTop: 12, color: "#166534" }}>同期完了: {syncedRoles} 件のロールを更新しました。</p>
			) : null}
			{hasError ? (
				<p style={{ marginTop: 12, color: "#b91c1c" }}>同期に失敗しました。しばらくしてから再実行してください。</p>
			) : null}
			<RoleAccordion categories={manifest.categories} roles={manifest.roles} />
		</main>
	);
}
