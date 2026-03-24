// 役割: ロール一覧表示

import styles from "./roles.module.css";

type RoleItem = {
	role_id: string;
	name: string;
	position: number;
	color: string;
};

type RoleListProps = {
	roles: RoleItem[];
	showHeader?: boolean;
};

export default function RoleList({ roles, showHeader = true }: RoleListProps) {
	if (roles.length === 0) {
		return <p className={styles.empty}>ロールがありません</p>;
	}

	const sorted = roles.slice().sort((a, b) => b.position - a.position);

	return (
		<div>
			{showHeader ? (
				<div className={styles.tableHeader}>
					<span>ロール</span>
					<span>メンバー</span>
					<span style={{ textAlign: "right" }}>操作</span>
				</div>
			) : null}
			{sorted.map((role) => (
				<div key={role.role_id} className={styles.roleRow}>
					<div className={styles.roleNameWrap}>
						<span className={styles.roleDot} style={{ backgroundColor: role.color }} />
						<span className={styles.roleName}>{role.name}</span>
					</div>
					<span className={styles.memberCol}>-</span>
					<div className={styles.actionCol}>
						<button type="button" className={styles.actionButton} aria-label={`${role.name} view`}>
							View
						</button>
						<button type="button" className={styles.actionButton} aria-label={`${role.name} edit`}>
							Edit
						</button>
					</div>
				</div>
			))}
		</div>
	);
}
