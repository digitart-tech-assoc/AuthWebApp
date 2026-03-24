// 役割: ロール管理画面

import { fetchManifest } from "@/actions/manifest";
import { triggerSync } from "@/actions/sync";
import RoleAccordion from "@/components/roles/RoleAccordion";

async function SyncButton() {
	async function runSync() {
		"use server";
		await triggerSync();
	}

	return (
		<form action={runSync}>
			<button type="submit">同期を実行</button>
		</form>
	);
}

export default async function RolesPage() {
	const manifest = await fetchManifest();

	return (
		<main style={{ padding: 24 }}>
			<h1>ロール管理</h1>
			<p>FastAPIが保持するあるべき状態を表示します。</p>
			<SyncButton />
			<RoleAccordion categories={manifest.categories} roles={manifest.roles} />
		</main>
	);
}
