// 役割: カテゴリアコーディオン

"use client";

import { useMemo, useState } from "react";

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
	const normalizedQuery = query.trim().toLowerCase();

	const filteredRoles = useMemo(() => {
		if (!normalizedQuery) {
			return roles;
		}
		return roles.filter((role) => role.name.toLowerCase().includes(normalizedQuery));
	}, [normalizedQuery, roles]);

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
					<span className={styles.meta}>ロール {filteredRoles.length}</span>
				</div>
				<div className={styles.group}>
					<div className={styles.groupHeader}>ロール一覧</div>
					<RoleList roles={filteredRoles} />
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
				<span className={styles.meta}>ロール {filteredRoles.length}</span>
			</div>
			{categories.map((category) => {
				const filtered = filteredRoles.filter((r) => r.category_id === category.id);
				if (filtered.length === 0) {
					return null;
				}
				return (
					<div key={category.id} className={styles.group}>
						<div className={styles.groupHeader}>{category.name}</div>
						<RoleList roles={filtered} />
					</div>
				);
			})}
			{uncategorizedRoles.length > 0 ? (
				<div className={styles.group}>
					<div className={styles.groupHeader}>カテゴリ未設定</div>
					<RoleList roles={uncategorizedRoles} />
				</div>
			) : null}
		</div>
	);
}
