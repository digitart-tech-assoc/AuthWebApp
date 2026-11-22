// 役割: マニフェストの保存エラーを、利用者向けの文言にする

import type { Member, Role } from "@/types/roles";

/** 保存エラーの detail から取り出した、原因の情報（#263）。形式が合わない項目は undefined にする */
export type SaveErrorCause = {
  code?: string;
  /** membership_assignment_invalid / assignment_change_conflict: 原因のメンバーの Discord ID */
  discordId?: string;
  /** membership_assignment_invalid: 原因の会員種別 */
  membershipTypes?: string[];
  /** membership_assignment_invalid: partial（一部だけ付け外し）/ exclusive（同時に持てない組） */
  reason?: string;
  /** protected_role_assignment / assignment_change_conflict: 原因のロール ID */
  roleId?: string;
};

// 画面に出す種別名。Backend の値をそのまま表示しないよう、ここにある種別だけを扱う
const MEMBERSHIP_TYPE_LABELS: Record<string, string> = {
  member: "member",
  sub_user: "sub垢",
  pre_member: "pre-member",
  obog: "OB/OG",
};

const SNOWFLAKE_PATTERN = /^\d+$/;

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

/** エラーレスポンスの detail から原因の情報を取り出す（取り出せなければ空のオブジェクト） */
export async function readSaveErrorCause(res: Response): Promise<SaveErrorCause> {
  try {
    const body: unknown = await res.json();
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (typeof detail !== "object" || detail === null) return {};
    const d = detail as Record<string, unknown>;
    const types = d.membership_types;
    return {
      code: asString(d.code),
      discordId: asString(d.discord_id),
      membershipTypes:
        Array.isArray(types) && types.every((t) => typeof t === "string") ? (types as string[]) : undefined,
      reason: asString(d.reason),
      roleId: asString(d.role_id),
    };
  } catch {
    return {};
  }
}

/** 原因のメンバーの表示名。読み込み済みの一覧になければ ID を返す。ID の形式でなければ undefined */
function memberLabel(discordId: string | undefined, members: Member[]): string | undefined {
  if (!discordId) return undefined;
  const member = members.find((m) => m.user_id === discordId);
  if (member) return `${member.display_name || member.username} さん`;
  return SNOWFLAKE_PATTERN.test(discordId) ? `Discord ID ${discordId} のメンバー` : undefined;
}

/** 原因のロールの表示名。画面の一覧になければ ID を返す。ID の形式でなければ undefined */
function roleLabel(roleId: string | undefined, roles: Role[]): string | undefined {
  if (!roleId) return undefined;
  const role = roles.find((r) => r.role_id === roleId);
  if (role) return `ロール「${role.name}」`;
  return SNOWFLAKE_PATTERN.test(roleId) ? `ロール（ID ${roleId}）` : undefined;
}

/** 原因のメンバーと種別を示す文言。必要な情報がそろわなければ undefined */
function membershipCauseMessage(cause: SaveErrorCause, members: Member[]): string | undefined {
  const who = memberLabel(cause.discordId, members);
  const types = cause.membershipTypes?.map((t) => MEMBERSHIP_TYPE_LABELS[t]);
  if (!who || !types || types.length === 0 || types.some((t) => t === undefined)) return undefined;
  if (cause.reason === "exclusive" && types.length === 2) {
    return `${who}: 会員種別 ${types[0]} と ${types[1]} のロールは同時に付けられません。`;
  }
  if (cause.reason === "partial" && types.length === 1) {
    return `${who}: 会員種別 ${types[0]} のロールは、すべて付けるか、すべて外してください。`;
  }
  return undefined;
}

/**
 * マニフェストの保存に失敗したときの文言。
 * Backend の文言（detail.message）は使わず、detail.code で出し分ける（#251、docs/logging-and-errors.md §3.3）。
 * 原因の ID が分かる場合は、画面に読み込み済みの一覧から名前を引いて示す（#263）。
 */
export function saveErrorMessage(cause: SaveErrorCause, roles: Role[], members: Member[]): string {
  switch (cause.code) {
    case "membership_assignment_invalid": {
      const detail = membershipCauseMessage(cause, members);
      if (detail) return `保存できませんでした。${detail}`;
      return "会員種別のロールの組み合わせが正しくないため、保存できませんでした。member と sub垢、pre-member と member・sub垢 は同時に付けられません。種別のロールが複数ある場合は、すべて付けるか、すべて外してください。";
    }
    case "protected_role_assignment": {
      const role = roleLabel(cause.roleId, roles);
      if (role) {
        return `保存できませんでした。${role}は Bot が操作できないため、割当を変更できません。Discord で直接変更してください。`;
      }
      return "Bot が操作できないロール（admin など）の割当が含まれているため、保存できませんでした。これらのロールは Discord で直接変更してください。";
    }
    case "assignment_change_conflict": {
      // 画面は差分から added / removed を作るため通常は起きない（#228）
      const role = roleLabel(cause.roleId, roles);
      const who = memberLabel(cause.discordId, members);
      if (role && who) {
        return `保存できませんでした。${role}で、${who}の追加と削除が同時に指定されています。画面を再読み込みしてから、もう一度変更してください。`;
      }
      return "同じメンバーの追加と削除が同時に指定されているため、保存できませんでした。画面を再読み込みしてから、もう一度変更してください。";
    }
    case "discord_unavailable":
      return "Discord からロールの情報を取得できなかったため、保存できませんでした。時間をおいて再度お試しください。";
    default:
      return "保存に失敗しました。再度お試しください。";
  }
}
