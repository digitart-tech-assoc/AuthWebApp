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

import { btnCompact } from "./roleStyles";

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
  onEdit?: (role: RoleItem) => void;
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
  onEdit?: () => void;
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
    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" className="shrink-0">
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
  onEdit,
}: SortableRoleRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: role.role_id, disabled: !enableDrag });

  // dnd-kit の位置・遷移は実行時の値のため style で指定する（styling-guide.md「インラインスタイルの例外」）
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const rowStateClass = isDisabled
    ? "cursor-not-allowed bg-slate-50 opacity-50"
    : isSelected
    ? "bg-indigo-50 hover:bg-indigo-100"
    : "hover:bg-slate-50";

  const dotColor =
    !role.color || role.color === "#000000" ? "#d1d5db" : role.color;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex min-h-10 items-center border-b border-slate-100 pr-3.5 pl-2.5 transition-colors last:border-b-0 ${rowStateClass}`}
      title={isDisabled ? "Botロール以上は編集できません" : undefined}
    >
      {/* Col 1: handle or checkbox */}
      <div className="flex w-8 shrink-0 items-center justify-center">
        {onToggle ? (
          <input
            type="checkbox"
            className="size-4 shrink-0 cursor-pointer accent-blue-600 disabled:cursor-not-allowed"
            checked={isSelected}
            onChange={onToggle}
            aria-label={`${role.name} を選択`}
            disabled={isDisabled}
          />
        ) : (
          <button
            type="button"
            className={`flex size-6 items-center justify-center rounded-md p-0 text-slate-300 transition-colors hover:bg-slate-100 hover:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-30 ${isDisabled ? "cursor-not-allowed" : "cursor-grab active:cursor-grabbing"}`}
            aria-label={`${role.name} 並び替え`}
            disabled={!enableDrag || isDisabled}
            {...attributes}
            {...(isDisabled ? {} : listeners)}
          >
            <DragIcon />
          </button>
        )}
      </div>

      {/* Col 2: dot + name */}
      <div className={`flex min-w-0 flex-1 items-center gap-2 py-2 ${isDisabled ? "cursor-not-allowed" : ""}`}>
        <span
          className={`size-2.5 shrink-0 rounded-full border border-slate-200 ${isDisabled ? "opacity-30" : ""}`}
          style={{ backgroundColor: dotColor }}
        />
        <span className={`truncate text-sm font-medium ${isDisabled ? "text-slate-400" : "text-slate-900"}`}>{role.name}</span>
      </div>

      {/* Col 3: action buttons */}
      <div className="flex shrink-0 items-center justify-end gap-2 sm:min-w-50">
        {onMembers && !onToggle && !isDisabled && (
          <button
            type="button"
            className={`${btnCompact} border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-indigo-600`}
            onClick={onMembers}
            aria-label={`${role.name} のメンバー編集`}
            title="メンバーを編集"
          >
            メンバー
          </button>
        )}
        {onEdit && !onToggle && !isDisabled && (
          <button
            type="button"
            className={`${btnCompact} border-slate-200 bg-white text-slate-600 hover:border-orange-200 hover:bg-orange-50 hover:text-orange-700`}
            onClick={onEdit}
            aria-label={`${role.name} を編集`}
            title="ロールを編集"
          >
            編集
          </button>
        )}
        {onPermissions && !onToggle && !isDisabled && (
          <button
            type="button"
            className={`${btnCompact} border-slate-200 bg-white text-slate-600 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800`}
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
            className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-sm text-red-600 transition-colors hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            onClick={onDelete}
            aria-label={`${role.name} を削除`}
            title="ロールを削除"
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
  onEdit,
  botPosition,
}: RoleListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  );

  if (roles.length === 0) {
    return <p className="px-4 py-5 text-center text-sm text-slate-500">ロールがありません</p>;
  }
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
        <div className="flex items-center border-b border-slate-100 py-2 pr-3.5 pl-2.5 text-xs font-bold uppercase tracking-wider text-slate-500">
          <span className="w-8 shrink-0" />
          <span className="flex-1">ロール名</span>
          {onPermissions && <span className="text-right">権限</span>}
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
                onEdit={
                  onEdit ? () => onEdit(role) : undefined
                }
              />
            );
          })}
        </SortableContext>
      </DndContext>
    </div>
  );
}
