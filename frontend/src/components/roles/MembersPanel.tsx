// 役割: メンバーリスト表示・管理コンポーネント

"use client";

import { useEffect, useState, useCallback } from "react";
import { syncMembers, getMembers, type MemberListsData, type MemberItem } from "@/actions/members";
import styles from "./roles.module.css";

export default function MembersPanel() {
	const [loading, setLoading] = useState(false);
	const [syncing, setSyncing] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [members, setMembers] = useState<MemberListsData | null>(null);

	// 初期ロード
	useEffect(() => {
		const load = async () => {
			try {
				setLoading(true);
				const data = await getMembers();
				setMembers(data);
			} catch (err) {
				const msg = err instanceof Error ? err.message : String(err);
				setError(msg);
			} finally {
				setLoading(false);
			}
		};

		load();
	}, []);

	// 同期ボタンハンドラ
	const handleSync = useCallback(async () => {
		try {
			setSyncing(true);
			setError(null);
			const result = await syncMembers();
			if (result.ok) {
				// 再読込
				const updated = await getMembers();
				setMembers(updated);
			}
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			setError(msg);
		} finally {
			setSyncing(false);
		}
	}, []);

	if (loading) {
		return <div style={{ padding: 16, color: "#888" }}>メンバーリストを読み込み中...</div>;
	}

	return (
		<div style={{ marginTop: 24, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8 }}>
			<h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 18, fontWeight: 600 }}>
				メンバーリスト管理
			</h2>

			{error && (
				<p style={{ marginBottom: 16, color: "#b91c1c" }}>
					エラー: {error}
				</p>
			)}

			<button
				onClick={handleSync}
				disabled={syncing}
				style={{
					padding: "8px 16px",
					marginBottom: 16,
					backgroundColor: syncing ? "#d1d5db" : "#3b82f6",
					color: "white",
					border: "none",
					borderRadius: 4,
					cursor: syncing ? "not-allowed" : "pointer",
					fontSize: 14,
				}}
			>
				{syncing ? "同期中..." : "Discord から同期"}
			</button>

			{members && (
				<div>
					<div style={{ marginBottom: 16 }}>
						<h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600 }}>
							メンバー ({members.member_list.length})
						</h3>
						<div style={{ maxHeight: 200, overflowY: "auto", fontSize: 12 }}>
							{members.member_list.length === 0 ? (
								<p style={{ color: "#888" }}>メンバーなし</p>
							) : (
								<ul style={{ margin: 0, paddingLeft: 20 }}>
									{members.member_list.map((m: MemberItem) => (
										<li key={m.discord_id} style={{ marginBottom: 4 }}>
											{m.discord_id} {m.assigned_at ? `(${new Date(m.assigned_at).toLocaleDateString()})` : ""}
										</li>
									))}
								</ul>
							)}
						</div>
					</div>

					<div style={{ marginBottom: 16 }}>
						<h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600 }}>
							管理者 ({members.admin_list.length})
						</h3>
						<div style={{ maxHeight: 200, overflowY: "auto", fontSize: 12 }}>
							{members.admin_list.length === 0 ? (
								<p style={{ color: "#888" }}>管理者なし</p>
							) : (
								<ul style={{ margin: 0, paddingLeft: 20 }}>
									{members.admin_list.map((m: MemberItem) => (
										<li key={m.discord_id} style={{ marginBottom: 4 }}>
											{m.discord_id} {m.assigned_at ? `(${new Date(m.assigned_at).toLocaleDateString()})` : ""}
										</li>
									))}
								</ul>
							)}
						</div>
					</div>

					<div>
						<h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600 }}>
							入会予定メンバー ({members.pre_member_list.length})
						</h3>
						<div style={{ maxHeight: 200, overflowY: "auto", fontSize: 12 }}>
							{members.pre_member_list.length === 0 ? (
								<p style={{ color: "#888" }}>入会予定メンバーなし</p>
							) : (
								<ul style={{ margin: 0, paddingLeft: 20 }}>
									{members.pre_member_list.map((m: MemberItem) => (
										<li key={m.discord_id} style={{ marginBottom: 4 }}>
											{m.discord_id} {m.assigned_at ? `(${new Date(m.assigned_at).toLocaleDateString()})` : ""}
										</li>
									))}
								</ul>
							)}
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
