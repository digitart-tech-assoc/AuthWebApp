// 役割: ロール一覧表示（DnD・チェックボックス・権限ボタン対応）

"use client";

import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import styles from "./roles.module.css";

type RoleItem = {
  role_id: string;
  name: string;
  position: number;
  color: string;
  permissions: number;
  hoist: boolean;
  mentionable: boolean;
  category_id: string | null;
};

type RoleListProps = {
  roles: RoleItem[];
  showHeader?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (roleId: string) => void;
  onReorder?: (orderedRoleIds: string[]) => void;
  onPermissions?: (role: RoleItem) => void;
  onDelete?: (roleId: string) => void;
  onMembers?: (role: RoleItem) => void;
  botPosition?: number;
};

type SortableRoleRowProps = {
  role: RoleItem;
  enableDrag: boolean;
  isSelected: boolean;
  isDisabled: boolean;
  onToggle?: () => void;
  onPermissions?: () => void;
  onDelete?: () => void;
  onMembers?: () => void;
};

function DragIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 12 12" fill="currentColor">
      <circle cx="3.5" cy="2" r="1.2" />
      <circle cx="8.5" cy="2" r="1.2" />
      <circle cx="3.5" cy="6" r="1.2" />
      <circle cx="8.5" cy="6" r="1.2" />
      <circle cx="3.5" cy="10" r="1.2" />
      <circle cx="8.5" cy="10" r="1.2" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M8 1L2 4v4c0 3.5 2.5 6.5 6 7.5C12.5 14.5 14 11.5 14 8V4L8 1z" />
    </svg>
  );
}

function SortableRoleRow({
  role,
  enableDrag,
  isSelected,
  isDisabled,
  onToggle,
  onPermissions,
  onDelete,
  onMembers,
}: SortableRoleRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: role.role_id, disabled: !enableDrag });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
  };

  const dotColor =
    !role.color || role.color === "#000000" ? "#d1d5db" : role.color;

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        cursor: isDisabled ? 'not-allowed' : undefined,
        opacity: isDisabled ? 0.5 : 1,
      }}
      className={`${styles.roleRow} ${isSelected ? styles.selected : ""} ${isDisabled ? styles.disabledRow : ""}`}
      title={isDisabled ? "Botロール以上は編集できません" : undefined}
    >
      {/* Col 1: handle or checkbox */}
      <div className={styles.roleHandleCell}>
        {onToggle ? (
          <input
            type="checkbox"
            className={styles.roleCheckbox}
            checked={isSelected}
            onChange={onToggle}
            aria-label={`${role.name} を選択`}
            disabled={isDisabled}
          />
        ) : (
          <button
            type="button"
            className={styles.dragHandle}
            aria-label={`${role.name} 並び替え`}
            disabled={!enableDrag || isDisabled}
            style={{ cursor: isDisabled ? 'not-allowed' : 'grab' }}
            {...attributes}
            {...(isDisabled ? {} : listeners)}
          >
            <DragIcon />
          </button>
        )}
      </div>

      {/* Col 2: dot + name */}
      <div className={styles.roleNameWrap} style={{ cursor: isDisabled ? 'not-allowed' : undefined }}>
        <span className={styles.roleDot} style={{ backgroundColor: dotColor }} />
        <span className={styles.roleName}>{role.name}</span>
      </div>

      {/* Col 3: action buttons */}
      <div className={styles.roleActionCol} style={{ display: 'flex', gap: '8px', alignItems: 'center', justifyContent: 'flex-end', minWidth: '160px' }}>
        {onMembers && !onToggle && (
          <button
            type="button"
            className={styles.membersBtn}
            onClick={onMembers}
            aria-label={`${role.name} のメンバー編集`}
            title="メンバーを編集"
          >
            メンバー
          </button>
        )}
        {onPermissions && !onToggle && !isDisabled && (
          <button
            type="button"
            className={styles.permBtn}
            onClick={onPermissions}
            aria-label={`${role.name} の権限設定`}
            title="権限設定"
          >
            <ShieldIcon />
            権限
          </button>
        )}
        
        {onDelete && !onToggle && !isDisabled && (
          <button
            type="button"
            className={styles.roleDeleteBtn}
            onClick={onDelete}
            aria-label={`${role.name} を削除`}
            title="ロールを削除"
            style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '14px', padding: '4px' }}
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

export default function RoleList({
  roles,
  showHeader = true,
  selectedIds,
  onToggleSelect,
  onReorder,
  onPermissions,
  onDelete,
  onMembers,
  botPosition,
}: RoleListProps) {
  if (roles.length === 0) {
    return <p className={styles.empty}>ロールがありません</p>;
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  );
  const enableDrag = typeof onReorder === "function" && !onToggleSelect;

  function handleDragEnd(event: DragEndEvent) {
    if (!onReorder || !event.over || event.active.id === event.over.id) {
      return;
    }
    const ids = roles.map((r) => r.role_id);
    const oldIndex = ids.indexOf(String(event.active.id));
    const newIndex = ids.indexOf(String(event.over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    const nextIds = ids.slice();
    const [moved] = nextIds.splice(oldIndex, 1);
    nextIds.splice(newIndex, 0, moved);
    onReorder(nextIds);
  }

  return (
    <div>
      {showHeader && (
        <div className={styles.tableHeader}>
          <span />
          <span>ロール名</span>
          {onPermissions && <span style={{ textAlign: "right" }}>権限</span>}
        </div>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={roles.map((r) => r.role_id)}
          strategy={verticalListSortingStrategy}
        >
          {roles.map((role) => {
            const isDisabled = botPosition !== undefined && role.position >= botPosition;
            return (
              <SortableRoleRow
                key={role.role_id}
                role={role}
                enableDrag={enableDrag && !isDisabled}
                isSelected={selectedIds?.has(role.role_id) ?? false}
                isDisabled={isDisabled}
                onToggle={
                  onToggleSelect
                    ? () => onToggleSelect(role.role_id)
                    : undefined
                }
                onPermissions={
                  onPermissions ? () => onPermissions(role) : undefined
                }
                onDelete={
                  onDelete ? () => onDelete(role.role_id) : undefined
                }
                onMembers={
                  onMembers ? () => onMembers(role) : undefined
                }
              />
            );
          })}
        </SortableContext>
      </DndContext>
    </div>
  );
}
