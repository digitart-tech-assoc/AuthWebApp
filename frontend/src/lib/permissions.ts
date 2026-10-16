// 役割: ロールに基づくアプリケーション操作権限の判定ユーティリティ

const MEMBER_PRIVILEGE_ROLES = new Set(["member", "sub_user", "obog", "admin"]);
const SELF_ROLE_VIEW_ROLES = new Set(["member", "sub_user", "obog"]);

/**
 * 会員相当の操作権限（ロール管理画面へのアクセス、プロフィール編集、自己ロール操作等）を持つか判定する。
 * member / sub_user / obog / admin が対象。
 */
export function hasMemberPrivilege(role: string | null | undefined): boolean {
	return Boolean(role && MEMBER_PRIVILEGE_ROLES.has(role));
}

/**
 * /roles 画面で個人用ロール管理ビュー（MemberSelfView）を利用する対象か判定する。
 * member / sub_user / obog は同一の個人用ロール管理権限を持つ。
 */
export function canUseSelfRoleView(role: string | null | undefined): boolean {
	return Boolean(role && SELF_ROLE_VIEW_ROLES.has(role));
}

/**
 * 全体ロール管理・メンバー管理の権限（admin）を持つか判定する。
 */
export function canManageAllRoles(role: string | null | undefined): boolean {
	return role === "admin";
}

