// 役割: ロール一覧表示

"use client";

import { DndContext, PointerSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

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
	onReorder?: (orderedRoleIds: string[]) => void;
};

type SortableRoleRowProps = {
	role: RoleItem;
	enableDrag: boolean;
};

function SortableRoleRow({ role, enableDrag }: SortableRoleRowProps) {
	const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
		id: role.role_id,
		disabled: !enableDrag,
	});

	const style = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.7 : 1,
	};

	return (
		<div ref={setNodeRef} style={style} className={styles.roleRow}>
			<div className={styles.roleNameWrap}>
				<button
					type="button"
					className={styles.dragHandle}
					aria-label={`${role.name} drag`}
					disabled={!enableDrag}
					{...attributes}
					{...listeners}
				>
					::
				</button>
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
	);
}

export default function RoleList({ roles, showHeader = true, onReorder }: RoleListProps) {
	if (roles.length === 0) {
		return <p className={styles.empty}>ロールがありません</p>;
	}

	const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
	const enableDrag = typeof onReorder === "function";

	function handleDragEnd(event: DragEndEvent) {
		if (!onReorder || !event.over || event.active.id === event.over.id) {
			return;
		}
		const ids = roles.map((role) => role.role_id);
		const oldIndex = ids.indexOf(String(event.active.id));
		const newIndex = ids.indexOf(String(event.over.id));
		if (oldIndex < 0 || newIndex < 0) {
			return;
		}
		const nextIds = ids.slice();
		const [moved] = nextIds.splice(oldIndex, 1);
		nextIds.splice(newIndex, 0, moved);
		onReorder(nextIds);
	}

	return (
		<div>
			{showHeader ? (
				<div className={styles.tableHeader}>
					<span>ロール</span>
					<span>メンバー</span>
					<span style={{ textAlign: "right" }}>操作</span>
				</div>
			) : null}
			<DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
				<SortableContext items={roles.map((role) => role.role_id)} strategy={verticalListSortingStrategy}>
					{roles.map((role) => (
						<SortableRoleRow key={role.role_id} role={role} enableDrag={enableDrag} />
					))}
				</SortableContext>
			</DndContext>
		</div>
	);
}
