"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SyncButton() {
	const router = useRouter();
	const [isPending, setIsPending] = useState(false);

	async function handleSync() {
		setIsPending(true);
		console.log("ロール同期リクエストを送信しました");
		try {
			const res = await fetch("/api/roles/refresh", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
			const body = (await res.json()) as { ok?: boolean; roles?: number };
			if (!res.ok || !body.ok) {
				router.push("/roles?error=1");
				return;
			}
			const roles = body.roles ?? 0;
			router.push(`/roles?synced=1&roles=${roles}`);
			router.refresh();
		} catch {
			router.push("/roles?error=1");
		} finally {
			setIsPending(false);
		}
	}

	return (
		<button type="button" onClick={handleSync} disabled={isPending}>
			{isPending ? "同期中..." : "同期を実行"}
		</button>
	);
}
