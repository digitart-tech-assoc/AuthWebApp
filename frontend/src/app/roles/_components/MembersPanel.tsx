// 役割: メンバーリスト表示・管理コンポーネント

"use client";

import { useEffect, useState, useCallback } from "react";
import { syncMembers, getMembers, type MemberListsData, type MemberItem } from "@/actions/members";
import { btnPrimary } from "./roleStyles";

/** メンバーリストの表示順と見出し（user_memberships の種別ごと） */
const MEMBER_LIST_SECTIONS: { key: keyof MemberListsData; label: string; emptyText: string }[] = [
	{ key: "member_list", label: "メンバー", emptyText: "メンバーなし" },
	{ key: "sub_user_list", label: "サブアカウント（sub垢）", emptyText: "サブアカウントなし" },
	{ key: "obog_list", label: "OB/OG", emptyText: "OB/OG なし" },
	{ key: "admin_list", label: "管理者", emptyText: "管理者なし" },
	{ key: "pre_member_list", label: "入会予定メンバー", emptyText: "入会予定メンバーなし" },
];

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
			} catch {
				// Backend のエラー文言は表示せず、固定文言を使う
				setError("メンバーリストの取得に失敗しました。時間をおいて再度お試しください。");
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
		} catch {
			setError("Discord からの同期に失敗しました。時間をおいて再度お試しください。");
		} finally {
			setSyncing(false);
		}
	}, []);

	if (loading) {
		return <div className="p-4 text-sm text-slate-500">メンバーリストを読み込み中...</div>;
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
					{MEMBER_LIST_SECTIONS.map(({ key, label, emptyText }) => (
						<div key={key} className="mb-4 last:mb-0">
							<h3 className="mb-2 text-sm font-semibold text-slate-900">
								{label} ({members[key].length})
							</h3>
							<div className="max-h-50 overflow-y-auto text-xs text-slate-700">
								{members[key].length === 0 ? (
									<p className="text-slate-500">{emptyText}</p>
								) : (
									<ul className="m-0 list-disc pl-5">
										{members[key].map((m: MemberItem) => (
											<li key={m.discord_id} className="mb-1">
												{m.discord_id} {m.assigned_at ? `(${new Date(m.assigned_at).toLocaleDateString()})` : ""}
											</li>
										))}
									</ul>
								)}
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
