// 役割: カテゴリアコーディオン

import RoleList from "./RoleList";

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
	if (categories.length === 0) {
		return (
			<div>
				<h2>ロール一覧</h2>
				<RoleList roles={roles} />
			</div>
		);
	}

	const categoryIds = new Set(categories.map((category) => category.id));
	const uncategorizedRoles = roles.filter(
		(role) => !role.category_id || !categoryIds.has(role.category_id),
	);

	return (
		<div>
			{categories.map((category) => {
				const filtered = roles.filter((r) => r.category_id === category.id);
				return (
					<details key={category.id} open={!category.is_collapsed}>
						<summary>{category.name}</summary>
						<RoleList roles={filtered} />
					</details>
				);
			})}
			{uncategorizedRoles.length > 0 ? (
				<details open>
					<summary>カテゴリ未設定</summary>
					<RoleList roles={uncategorizedRoles} />
				</details>
			) : null}
		</div>
	);
}
