// 役割: メンバーリスト表示・管理コンポーネント

"use client";

import { useEffect, useState, useCallback } from "react";
import { syncMembers, getMembers, type MemberListsData, type MemberItem } from "@/actions/members";
import { btnPrimary } from "./roleStyles";

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
		return <div className="p-4 text-sm text-slate-400">メンバーリストを読み込み中...</div>;
	}

	return (
		<div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
			<h2 className="mt-0 mb-4 text-lg font-semibold text-slate-900">
				メンバーリスト管理
			</h2>

			{error && (
				<p className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
					エラー: {error}
				</p>
			)}

			<button
				onClick={handleSync}
				disabled={syncing}
				className={`${btnPrimary} mb-4`}
			>
				{syncing ? "同期中..." : "Discord から同期"}
			</button>

			{members && (
				<div>
					<div className="mb-4">
						<h3 className="mb-2 text-sm font-semibold text-slate-900">
							メンバー ({members.member_list.length})
						</h3>
						<div className="max-h-50 overflow-y-auto text-xs text-slate-700">
							{members.member_list.length === 0 ? (
								<p className="text-slate-400">メンバーなし</p>
							) : (
								<ul className="m-0 list-disc pl-5">
									{members.member_list.map((m: MemberItem) => (
										<li key={m.discord_id} className="mb-1">
											{m.discord_id} {m.assigned_at ? `(${new Date(m.assigned_at).toLocaleDateString()})` : ""}
										</li>
									))}
								</ul>
							)}
						</div>
					</div>

					<div className="mb-4">
						<h3 className="mb-2 text-sm font-semibold text-slate-900">
							管理者 ({members.admin_list.length})
						</h3>
						<div className="max-h-50 overflow-y-auto text-xs text-slate-700">
							{members.admin_list.length === 0 ? (
								<p className="text-slate-400">管理者なし</p>
							) : (
								<ul className="m-0 list-disc pl-5">
									{members.admin_list.map((m: MemberItem) => (
										<li key={m.discord_id} className="mb-1">
											{m.discord_id} {m.assigned_at ? `(${new Date(m.assigned_at).toLocaleDateString()})` : ""}
										</li>
									))}
								</ul>
							)}
						</div>
					</div>

					<div>
						<h3 className="mb-2 text-sm font-semibold text-slate-900">
							入会予定メンバー ({members.pre_member_list.length})
						</h3>
						<div className="max-h-50 overflow-y-auto text-xs text-slate-700">
							{members.pre_member_list.length === 0 ? (
								<p className="text-slate-400">入会予定メンバーなし</p>
							) : (
								<ul className="m-0 list-disc pl-5">
									{members.pre_member_list.map((m: MemberItem) => (
										<li key={m.discord_id} className="mb-1">
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
