"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function PushButton() {
	const router = useRouter();
	const [isPending, setIsPending] = useState(false);

	async function handlePush() {
		setIsPending(true);
		console.log("ロールpushリクエストを送信しました");
		try {
			const res = await fetch("/api/roles/push", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
			const body = (await res.json()) as {
				ok?: boolean;
				updated?: number;
				created?: number;
				deleted?: number;
				reordered?: number;
			};
			if (!res.ok || !body.ok) {
				router.push("/roles?push_error=1");
				return;
			}
			const updated = body.updated ?? 0;
			const created = body.created ?? 0;
			const deleted = body.deleted ?? 0;
			const reordered = body.reordered ?? 0;
			router.push(`/roles?pushed=1&updated=${updated}&created=${created}&deleted=${deleted}&reordered=${reordered}`);
			router.refresh();
		} catch {
			router.push("/roles?push_error=1");
		} finally {
			setIsPending(false);
		}
	}

	return (
		<button type="button" onClick={handlePush} disabled={isPending}>
			{isPending ? "pushing..." : "push"}
		</button>
	);
}
