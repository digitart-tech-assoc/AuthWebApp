"""役割: アプリケーション全体の設定値・定数の集約

各モジュールに散らばっていたマジックナンバー、ロール名、メンバーシップ種別等の定数を一元管理する。
"""

from __future__ import annotations


class MembershipType:
	"""user_memberships で使用されるメンバーシップ種別の定数定義"""
	MEMBER = "member"
	ADMIN = "admin"
	PRE_MEMBER = "pre_member"
	OBOG = "obog"
	SUB_USER = "sub_user"

	ALL = (MEMBER, ADMIN, PRE_MEMBER, OBOG, SUB_USER)


# ============================================================================
# OTP (One-Time Password) 設定
# ============================================================================
OTP_EXPIRY_SECONDS: int = 600
OTP_EXPIRY_MINUTES: int = OTP_EXPIRY_SECONDS // 60
OTP_MAX_ATTEMPTS: int = 5
OTP_CODE_LENGTH: int = 6


# ============================================================================
# HTTP クライアントタイムアウト (秒)
# ============================================================================
DISCORD_API_TIMEOUT: float = 10.0
DISCORD_MEMBER_FETCH_TIMEOUT: float = 30.0


# ============================================================================
# Discord ロール名マッピング
# ============================================================================
MEMBER_ROLE_NAMES: set[str] = {"member", "会員", "Member"}
OBOG_ROLE_NAMES: set[str] = {"OBOG", "OB/OG", "OB-OG"}
ADMIN_ROLE_NAMES: set[str] = {"administrator", "管理者", "Administrator"}
PRE_MEMBER_ROLE_NAME: str = "pre-member"


# ============================================================================
# 編集制限付きロールカテゴリ名
# ============================================================================
RESTRICTED_CATEGORY_NAMES: set[str] = {"会員情報", "学部学科", "学年"}
MEMBER_RESTRICTED_CATEGORY_NAMES: set[str] = RESTRICTED_CATEGORY_NAMES  # 後方互換用別名


# ============================================================================
# メンバーシップ種別の優先度 SQL 断片
# 優先順位: admin(1) > member/sub_user(2) > pre_member(3) > obog(4)
# ============================================================================
MEMBERSHIP_PRIORITY_SQL: str = """
ORDER BY CASE membership_type 
	WHEN 'admin' THEN 1
	WHEN 'member' THEN 2
	WHEN 'sub_user' THEN 2
	WHEN 'pre_member' THEN 3
	WHEN 'obog' THEN 4
END
"""
