// 役割: ロール管理画面

import { fetchManifest } from "@/actions/manifest";
import PushButton from "@/components/roles/PushButton";
import RoleAccordion from "@/components/roles/RoleAccordion";
import SyncButton from "@/components/roles/SyncButton";

type RolesPageProps = {
	searchParams?:
		| {
			synced?: string;
			roles?: string;
			error?: string;
			pushed?: string;
			push_error?: string;
			updated?: string;
			created?: string;
			deleted?: string;
			reordered?: string;
		  }
		| Promise<{
		synced?: string;
		roles?: string;
		error?: string;
		pushed?: string;
		push_error?: string;
		updated?: string;
		created?: string;
		deleted?: string;
		reordered?: string;
	  }>;
};

export default async function RolesPage({ searchParams }: RolesPageProps) {
	const manifest = await fetchManifest();
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
			<div style={{ display: "flex", gap: 8 }}>
				<SyncButton />
				<PushButton />
			</div>
			{synced && !hasError ? (
				<p style={{ marginTop: 12, color: "#166534" }}>同期完了: {syncedRoles} 件のロールを更新しました。</p>
			) : null}
			{hasError ? (
				<p style={{ marginTop: 12, color: "#b91c1c" }}>同期に失敗しました。しばらくしてから再実行してください。</p>
			) : null}
			{pushed && !pushError ? (
				<p style={{ marginTop: 12, color: "#166534" }}>
					push完了: updated={updated}, created={created}, deleted={deleted}, reordered={reordered}
				</p>
			) : null}
			{pushError ? (
				<p style={{ marginTop: 12, color: "#b91c1c" }}>pushに失敗しました。設定と権限を確認してください。</p>
			) : null}
			<RoleAccordion categories={manifest.categories} roles={manifest.roles} />
		</main>
	);
}
