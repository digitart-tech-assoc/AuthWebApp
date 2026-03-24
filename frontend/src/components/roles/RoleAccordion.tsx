// 役割: カテゴリアコーディオン

"use client";

import { useEffect, useMemo, useState } from "react";

import RoleList from "./RoleList";
import styles from "./roles.module.css";

type Category = {
	id: string;
	name: string;
	is_collapsed: boolean;
};

type Role = {
	role_id: string;
	name: string;
	hoist: boolean;
	mentionable: boolean;
	permissions: number;
	position: number;
	color: string;
	category_id: string | null;
};

type Props = {
	categories: Category[];
	roles: Role[];
};

export default function RoleAccordion({ categories, roles }: Props) {
	const [query, setQuery] = useState("");
	const [allRoles, setAllRoles] = useState<Role[]>([]);
	const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
	const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
	const normalizedQuery = query.trim().toLowerCase();

	useEffect(() => {
		setAllRoles(roles.slice().sort((a, b) => b.position - a.position));
		setHasUnsavedChanges(false);
		setSaveState("idle");
	}, [roles]);

	async function persistRoles(nextRoles: Role[]) {
		setSaveState("saving");
		try {
			const res = await fetch("/api/manifest", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ categories, roles: nextRoles }),
			});
			if (!res.ok) {
				setSaveState("error");
				return;
			}
			setHasUnsavedChanges(false);
			setSaveState("saved");
		} catch {
			setSaveState("error");
		}
	}

	async function handleSaveOrder() {
		if (saveState === "saving" || !hasUnsavedChanges) {
			return;
		}
		await persistRoles(allRoles);
	}

	function reorderGroup(orderedRoleIds: string[]) {
		const targetIds = new Set(orderedRoleIds);
		const roleMap = new Map(allRoles.map((role) => [role.role_id, role]));
		const reorderedGroup = orderedRoleIds
			.map((id) => roleMap.get(id))
			.filter((role): role is Role => Boolean(role));

		if (reorderedGroup.length !== orderedRoleIds.length) {
			return;
		}

		let pointer = 0;
		const reordered = allRoles.map((role) => {
			if (!targetIds.has(role.role_id)) {
				return role;
			}
			const nextRole = reorderedGroup[pointer];
			pointer += 1;
			return nextRole;
		});

		const total = reordered.length;
		const withPosition = reordered.map((role, index) => ({
			...role,
			position: total - index,
		}));

		setAllRoles(withPosition);
		setHasUnsavedChanges(true);
		setSaveState("idle");
	}

	const statusText =
		saveState === "saving"
			? "並び順を保存中..."
			: saveState === "saved"
				? "並び順を保存しました"
				: saveState === "error"
					? "並び順の保存に失敗しました"
					: hasUnsavedChanges
						? "未保存の変更があります"
						: null;

	const filteredRoles = useMemo(() => {
		if (!normalizedQuery) {
			return allRoles;
		}
		return allRoles.filter((role) => role.name.toLowerCase().includes(normalizedQuery));
	}, [allRoles, normalizedQuery]);

	if (categories.length === 0) {
		return (
			<div className={styles.board}>
				<div className={styles.toolbar}>
					<input
						type="search"
						className={styles.search}
						placeholder="ロールを検索"
						value={query}
						onChange={(e) => setQuery(e.target.value)}
					/>
					<div className={styles.toolbarRight}>
						<span className={styles.meta}>ロール {filteredRoles.length}</span>
						<button
							type="button"
							className={styles.saveButton}
							onClick={handleSaveOrder}
							disabled={saveState === "saving" || !hasUnsavedChanges}
						>
							保存
						</button>
						{statusText ? <span className={styles.meta}>{statusText}</span> : null}
					</div>
				</div>
				<div className={styles.group}>
					<div className={styles.groupHeader}>ロール一覧</div>
					<RoleList roles={filteredRoles} onReorder={reorderGroup} />
				</div>
			</div>
		);
	}

	const categoryIds = new Set(categories.map((category) => category.id));
	const uncategorizedRoles = filteredRoles.filter(
		(role) => !role.category_id || !categoryIds.has(role.category_id),
	);

	return (
		<div className={styles.board}>
			<div className={styles.toolbar}>
				<input
					type="search"
					className={styles.search}
					placeholder="ロールを検索"
					value={query}
					onChange={(e) => setQuery(e.target.value)}
				/>
				<div className={styles.toolbarRight}>
					<span className={styles.meta}>ロール {filteredRoles.length}</span>
					<button
						type="button"
						className={styles.saveButton}
						onClick={handleSaveOrder}
						disabled={saveState === "saving" || !hasUnsavedChanges}
					>
						保存
					</button>
					{statusText ? <span className={styles.meta}>{statusText}</span> : null}
				</div>
			</div>
			{categories.map((category) => {
				const filtered = filteredRoles.filter((r) => r.category_id === category.id);
				if (filtered.length === 0) {
					return null;
				}
				return (
					<div key={category.id} className={styles.group}>
						<div className={styles.groupHeader}>{category.name}</div>
						<RoleList roles={filtered} onReorder={reorderGroup} />
					</div>
				);
			})}
			{uncategorizedRoles.length > 0 ? (
				<div className={styles.group}>
					<div className={styles.groupHeader}>カテゴリ未設定</div>
					<RoleList roles={uncategorizedRoles} onReorder={reorderGroup} />
				</div>
			) : null}
		</div>
	);
}
