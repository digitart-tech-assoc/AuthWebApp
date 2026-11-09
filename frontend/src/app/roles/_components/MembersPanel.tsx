// 役割: メンバーリスト表示・管理コンポーネント

"use client";

import { useEffect, useState, useCallback } from "react";
import {
	syncMembers,
	getMembers,
	type DiffOnlyMembershipType,
	type MemberListResponse,
	type MemberListsData,
	type MemberItem,
} from "@/actions/members";
import { btnPrimary } from "./roleStyles";

/** メンバーリストの表示順と見出し（user_memberships の種別ごと） */
const MEMBER_LIST_SECTIONS: { key: keyof MemberListsData; label: string; emptyText: string }[] = [
	{ key: "member_list", label: "メンバー", emptyText: "メンバーなし" },
	{ key: "sub_user_list", label: "サブアカウント（sub垢）", emptyText: "サブアカウントなし" },
	{ key: "obog_list", label: "OB/OG", emptyText: "OB/OG なし" },
	{ key: "admin_list", label: "管理者", emptyText: "管理者なし" },
	{ key: "pre_member_list", label: "入会予定メンバー", emptyText: "入会予定メンバーなし" },
];

/** 同期で書き込まない種別の、差分の表示順と見出し（#251） */
const DIFF_SECTIONS: { type: DiffOnlyMembershipType; label: string }[] = [
	{ type: "member", label: "メンバー" },
	{ type: "sub_user", label: "サブアカウント（sub垢）" },
	{ type: "obog", label: "OB/OG" },
	{ type: "pre_member", label: "入会予定メンバー" },
];

/** Discord ID の一覧（差分の 1 方向分） */
function DiffIdList({ title, ids }: { title: string; ids: string[] }) {
	if (ids.length === 0) return null;
	return (
		<div className="mt-1">
			<p className="m-0 text-xs text-slate-600">
				{title}（{ids.length}）
			</p>
			<ul className="m-0 max-h-32 list-disc overflow-y-auto pl-5 text-xs text-slate-700">
				{ids.map((id) => (
					<li key={id}>{id}</li>
				))}
			</ul>
		</div>
	);
}

/** 同期の結果に含まれる、Discord のロールと会員種別の差分 */
function MembershipDiffSummary({ diff }: { diff: MemberListResponse["diff"] }) {
	const sections = DIFF_SECTIONS.map(({ type, label }) => ({ type, label, value: diff[type] }));
	const hasDiff = sections.some(
		({ value }) => value != null && (value.discord_only.length > 0 || value.db_only.length > 0),
	);

	return (
		<div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
			<h3 className="mt-0 mb-1 text-sm font-semibold text-slate-900">Discord のロールとの差分</h3>
			<p className="m-0 mb-2 text-xs text-slate-600">
				管理者以外の会員種別は、同期では変更しません。差分を直すときは、ロールの割当を変更して保存し、「変更を確定」で Discord に反映してください。
			</p>
			{!hasDiff ? (
				<p className="m-0 text-xs text-slate-500">差分はありません。</p>
			) : (
				sections.map(({ type, label, value }) => {
					if (value == null || (value.discord_only.length === 0 && value.db_only.length === 0)) return null;
					return (
						<div key={type} className="mb-2 last:mb-0">
							<p className="m-0 text-xs font-semibold text-slate-900">{label}</p>
							<DiffIdList title="Discord ではロールがあるが、会員種別がない" ids={value.discord_only} />
							<DiffIdList title="会員種別はあるが、Discord ではロールがない" ids={value.db_only} />
						</div>
					);
				})
			)}
		</div>
	);
}

export default function MembersPanel() {
	const [loading, setLoading] = useState(false);
	const [syncing, setSyncing] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [members, setMembers] = useState<MemberListsData | null>(null);
	const [diff, setDiff] = useState<MemberListResponse["diff"] | null>(null);

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
				setDiff(result.diff ?? null);
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

			{diff && <MembershipDiffSummary diff={diff} />}

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
