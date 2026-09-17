// ロール・権限・マニフェスト関連の共通型定義

export type Category = {
  id: string;
  name: string;
  display_order: number;
  is_collapsed: boolean;
  permissions: number;
  is_restricted: boolean;
};

export type Role = {
  role_id: string;
  name: string;
  hoist: boolean;
  mentionable: boolean;
  permissions: number;
  position: number;
  color: string;
  category_id: string | null;
  is_our_bot?: boolean;
};

export type ManifestCategory = Category;
export type ManifestRole = Omit<Role, "is_our_bot">;

export type Manifest = {
  categories: ManifestCategory[];
  roles: ManifestRole[];
};

export type Member = {
  user_id: string;
  username: string;
  display_name: string | null;
  avatar: string | null;
};

export type PermissionTarget = {
  /** "category" | "role" */
  kind: "category" | "role";
  id: string;
  name: string;
  /** For roles: the parent category permissions (for inheritance display) */
  categoryPermissions?: number;
  currentPermissions: number;
  roleDotColor?: string;
};

export type RoleDiffData = {
  roleAdded: { role: Role; memberCount: number }[];
  memberAssigned: { roleId: string; roleName: string; added: string[]; removed: string[] }[];
  permissionEdited: { roleId: string; roleName: string; oldPermissions: string; newPermissions: string }[];
  orderChanged: { roleId: string; roleName: string; oldPosition: number; newPosition: number }[];
  roleDeleted: Role[];
  categoriesAdded: Category[];
  categoriesDeleted: Category[];
};

