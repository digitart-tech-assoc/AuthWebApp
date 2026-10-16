// 役割: アプリロール（app_role）に基づく権限判定

/** アプリ上で member と同等の権限を持つロール（obog / sub_user は member と同じ操作が可能） */
const MEMBER_PRIVILEGED_ROLES: ReadonlySet<string> = new Set(["member", "sub_user", "obog"]);

/** 特権ユーザー（admin）か */
export function isAdmin(role: string | null | undefined): boolean {
	return role === "admin";
}

/** 会員向け機能を利用できるか（member / sub_user / obog のいずれか、または admin） */
export function hasMemberPrivilege(role: string | null | undefined): boolean {
	return isAdmin(role) || MEMBER_PRIVILEGED_ROLES.has(role ?? "");
}
