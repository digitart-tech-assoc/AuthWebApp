"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import RoleList from "./RoleList";
import styles from "./roles.module.css";
import type { Category, Role } from "@/types/roles";

import { ChevronRight, Shield } from "lucide-react";

// ===== SortableCategoryItem Props =====

export type SortableCategoryItemProps = {
  cat: Category;
  catRoles: Role[];
  isOpen: boolean;
  isRestrictedCat: boolean;
  memberCanManageCat: boolean;
  isAdmin: boolean;
  isMember: boolean;
  isSelectMode: boolean;
  selectedRoleIds: Set<string>;
  botPosition: number | undefined;
  onToggleCollapse: (id: string) => void;
  onOpenCategoryPermissions: (cat: Category) => void;
  onDeleteCategory: (id: string) => void;
  onToggleSelect: (id: string) => void;
  onReorder: ((ids: string[]) => void) | undefined;
  onOpenRolePermissions: ((role: Role) => void) | undefined;
  onDeleteRole: ((id: string) => void) | undefined;
  onOpenMemberModal: ((role: Role) => void) | undefined;
  onEditRole: ((role: Role) => void) | undefined;
  onEditCategory: ((cat: Category) => void) | undefined;
  styles?: Record<string, string>;
};

export default function SortableCategoryItem({
  cat,
  catRoles,
  isOpen,
  isRestrictedCat,
  memberCanManageCat,
  isAdmin,
  isMember,
  isSelectMode,
  selectedRoleIds,
  botPosition,
  onToggleCollapse,
  onOpenCategoryPermissions,
  onDeleteCategory,
  onToggleSelect,
  onReorder,
  onOpenRolePermissions,
  onDeleteRole,
  onOpenMemberModal,
  onEditRole,
  onEditCategory,
}: SortableCategoryItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: cat.id });
  const catStyle = {
    // scaleX/scaleYを1に固定してドラッグ時の引き伸ばしを防ぐ
    transform: CSS.Transform.toString(transform ? { ...transform, scaleX: 1, scaleY: 1 } : null),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={catStyle} className={styles.group}>
      <div
        className={styles.groupHeader}
        onClick={() => onToggleCollapse(cat.id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onToggleCollapse(cat.id);
        }}
      >
        <ChevronRight
          className={`${styles.chevron} ${isOpen ? styles.open : ""}`}
          size={16}
        />
        {/* Drag handle */}
        {(isAdmin || isMember) && (
          <span
            {...attributes}
            {...listeners}
            className={styles.dragHandle}
            title="ドラッグでカテゴリを並び替え"
            onClick={(e) => e.stopPropagation()}
            style={{ cursor: isDragging ? "grabbing" : "grab", padding: "0 4px", lineHeight: 1 }}
          >
            ⠿
          </span>
        )}
        <span className={styles.groupName}>{cat.name}</span>
        <span className={styles.groupCount}>{catRoles.length}</span>

        {isAdmin ? (
          <>
            <button
              type="button"
              className={styles.catPermBtn}
              onClick={(e) => {
                e.stopPropagation();
                if (onEditCategory) onEditCategory(cat);
              }}
              title="カテゴリ編集"
              aria-label={`${cat.name} を編集`}
            >
              編集
            </button>
            <button
              type="button"
              className={styles.catPermBtn}
              onClick={(e) => {
                e.stopPropagation();
                onOpenCategoryPermissions(cat);
              }}
              title="カテゴリ権限設定"
              aria-label={`${cat.name} の権限設定`}
            >
              <Shield size={11} />
              権限
            </button>
          </>
        ) : null}

        {/* member: ロールが残っている場合は削除不可。admin: 制限なし */}
        {isAdmin ? (
          <button
            type="button"
            className={styles.groupDeleteBtn}
            onClick={(e) => {
              e.stopPropagation();
              onDeleteCategory(cat.id);
            }}
            aria-label={`${cat.name} を削除`}
            title="カテゴリを削除"
          >
            ✕
          </button>
        ) : memberCanManageCat ? (
          <button
            type="button"
            className={`${styles.groupDeleteBtn} ${catRoles.length > 0 ? styles.btnDisabled ?? "" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              if (catRoles.length > 0) return;
              onDeleteCategory(cat.id);
            }}
            disabled={catRoles.length > 0}
            aria-label={`${cat.name} を削除`}
            title={
              catRoles.length > 0
                ? `カテゴリ内のロール（${catRoles.length}件）をすべて削除してからカテゴリを削除できます`
                : "カテゴリを削除"
            }
          >
            ✕
          </button>
        ) : null}
      </div>

      {isOpen && (
        <RoleList
          roles={catRoles}
          showHeader={false}
          selectedIds={isSelectMode ? selectedRoleIds : undefined}
          onToggleSelect={isSelectMode ? onToggleSelect : undefined}
          onReorder={!isSelectMode && isAdmin ? onReorder : undefined}
          onPermissions={!isSelectMode && isAdmin ? onOpenRolePermissions : undefined}
          onDelete={!isSelectMode && (isAdmin || memberCanManageCat) ? onDeleteRole : undefined}
          onMembers={!isSelectMode && (isAdmin || memberCanManageCat) ? onOpenMemberModal : undefined}
          onEdit={!isSelectMode && isAdmin ? onEditRole : undefined}
          botPosition={botPosition}
        />
      )}
    </div>
  );
}
