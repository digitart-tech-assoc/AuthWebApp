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
		</div>
	);
}
