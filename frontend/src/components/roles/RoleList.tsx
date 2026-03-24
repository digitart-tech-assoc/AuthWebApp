// 役割: ロール一覧表示

type RoleItem = {
	role_id: string;
	name: string;
	position: number;
	color: string;
};

type RoleListProps = {
	roles: RoleItem[];
};

export default function RoleList({ roles }: RoleListProps) {
	if (roles.length === 0) {
		return <p>ロールがありません</p>;
	}

	return (
		<ul>
			{roles
				.slice()
				.sort((a, b) => b.position - a.position)
				.map((role) => (
					<li key={role.role_id}>
						<span
							style={{
								display: "inline-block",
								width: 10,
								height: 10,
								borderRadius: "50%",
								backgroundColor: role.color,
								marginRight: 8,
							}}
						/>
						{role.name} (pos: {role.position})
					</li>
				))}
		</ul>
	);
}
