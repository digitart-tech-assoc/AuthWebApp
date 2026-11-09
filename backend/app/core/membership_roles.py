"""役割: 会員種別ごとの Discord ロール ID の設定（#234）

会員種別（admin / member / obog / sub_user / pre_member）は Discord のロール名ではなく、
環境変数で指定したロール ID で判定する。ロール名で判定すると、同じ名前のロールを作る・
既存ロールを予約名にリネームするだけで種別（admin を含む）が付与されてしまうため。

環境変数はテストや設定変更に追従できるよう、呼び出しのたびに読む。
"""

from __future__ import annotations

import logging
import os

from app.core.config import MembershipType

logger = logging.getLogger(__name__)

# 会員種別 -> ロール ID を読む環境変数（PRE_MEMBER_ROLE_ID は既存の名前に合わせて単数形）
MEMBERSHIP_ROLE_ID_ENV_VARS: dict[str, str] = {
	MembershipType.ADMIN: "ADMIN_ROLE_IDS",
	MembershipType.MEMBER: "MEMBER_ROLE_IDS",
	MembershipType.OBOG: "OBOG_ROLE_IDS",
	MembershipType.SUB_USER: "SUB_USER_ROLE_IDS",
	MembershipType.PRE_MEMBER: "PRE_MEMBER_ROLE_ID",
}

# 未設定だと認可や入会フローが成り立たない種別。本番では未設定なら起動しない
REQUIRED_MEMBERSHIP_TYPES: tuple[str, ...] = (
	MembershipType.ADMIN,
	MembershipType.MEMBER,
	MembershipType.PRE_MEMBER,
)


def _parse_ids(raw: str) -> tuple[str, ...]:
	"""カンマ区切りの ID を、空要素と重複を除いて指定順のまま返す。"""
	ids: list[str] = []
	for part in raw.split(","):
		role_id = part.strip()
		if role_id and role_id not in ids:
			ids.append(role_id)
	return tuple(ids)


def membership_role_ids() -> dict[str, tuple[str, ...]]:
	"""会員種別ごとに、設定されたロール ID を返す（未設定の種別は空タプル）。"""
	return {
		m_type: _parse_ids(os.getenv(env_var, ""))
		for m_type, env_var in MEMBERSHIP_ROLE_ID_ENV_VARS.items()
	}


def missing_membership_role_id_env_vars(types: tuple[str, ...] | None = None) -> list[str]:
	"""ロール ID が設定されていない種別の環境変数名を返す。types を省略した場合は全種別を確認する。"""
	configured = membership_role_ids()
	targets = types if types is not None else tuple(MEMBERSHIP_ROLE_ID_ENV_VARS)
	return [MEMBERSHIP_ROLE_ID_ENV_VARS[m_type] for m_type in targets if not configured[m_type]]


def validate_membership_role_ids(env: str) -> None:
	"""会員種別のロール ID の設定を確認する。

	必須の種別が未設定の場合、本番では起動を止め、それ以外では警告する。
	任意の種別（obog / sub_user）が未設定の場合は警告のみ（その種別は /members/sync で差分を計算しない）。
	メッセージにはロール ID の値を出さない。
	"""
	missing_required = missing_membership_role_id_env_vars(REQUIRED_MEMBERSHIP_TYPES)
	optional_types = tuple(t for t in MEMBERSHIP_ROLE_ID_ENV_VARS if t not in REQUIRED_MEMBERSHIP_TYPES)
	missing_optional = missing_membership_role_id_env_vars(optional_types)

	if missing_optional:
		logger.warning(
			"Membership role IDs are not set: %s (these membership types are not synced from Discord)",
			", ".join(missing_optional),
		)
	if not missing_required:
		return

	reason = f"Required membership role IDs are not set: {', '.join(missing_required)}"
	if env == "production":
		raise RuntimeError(reason)
	logger.warning("%s (allowed only outside production)", reason)
