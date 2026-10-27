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
	# アプリ上で member と同等の権限を持つ種別（obog / sub_user は member と同じ操作が可能）
	MEMBER_PRIVILEGED = (MEMBER, SUB_USER, OBOG)


# ============================================================================
# OTP (One-Time Password) 設定
# ============================================================================
OTP_EXPIRY_SECONDS: int = 600
OTP_EXPIRY_MINUTES: int = OTP_EXPIRY_SECONDS // 60
OTP_MAX_ATTEMPTS: int = 5
OTP_CODE_LENGTH: int = 6
# OTP 検証時の行ロック（SELECT ... FOR UPDATE）を待つ上限（ミリ秒）。
# 同じ OTP への並行リクエストがコネクションを握ったまま待ち続け、プールを枯渇させるのを防ぐ
OTP_LOCK_TIMEOUT_MS: int = 3000


# ============================================================================
# 外部サービスへの送信を起こすエンドポイントのレート制限（#82）
# ============================================================================
# 学生 OTP 送信: discord_id ごとに窓の秒数あたり最大回数
OTP_SEND_RATE_LIMIT: int = 3
OTP_SEND_RATE_WINDOW_SECONDS: int = 600
# 入会申請（OTP メール送信）: IP ごとに窓の秒数あたり最大回数
JOIN_REQUEST_RATE_LIMIT: int = 5
JOIN_REQUEST_RATE_WINDOW_SECONDS: int = 600
# 大学のネットワークからの入会申請の上限。学内 Wi-Fi は多くの利用者が同じグローバル IP を共有するため大幅に緩める
JOIN_REQUEST_RELAXED_RATE_LIMIT: int = 50
RATE_LIMIT_RELAXED_NETWORKS: tuple[str, ...] = ("133.2.0.0/16",)
# お問い合わせ送信（Discord チャンネルへの投稿）: IP ごとに窓の秒数あたり最大回数
CONTACT_RATE_LIMIT: int = 5
CONTACT_RATE_WINDOW_SECONDS: int = 3600
# member によるロール作成（Discord へのロール作成）: discord_id ごとに窓の秒数あたり最大回数
ROLE_SELF_CREATE_RATE_LIMIT: int = 5
ROLE_SELF_CREATE_RATE_WINDOW_SECONDS: int = 600


# ============================================================================
# HTTP クライアントタイムアウト (秒)
# ============================================================================
DISCORD_API_TIMEOUT: float = 10.0
DISCORD_MEMBER_FETCH_TIMEOUT: float = 30.0


# ============================================================================
# Discord API のレート制限（429）再試行
# ============================================================================
# 429 を受けたときに再試行する最大回数
DISCORD_RATE_LIMIT_MAX_RETRIES: int = 3
# 1 回の待ち時間の上限 (秒)。retry_after がこれを超える場合は待たずに失敗とする
DISCORD_RATE_LIMIT_MAX_WAIT: float = 10.0


# ============================================================================
# Discord ロール名マッピング
# ============================================================================
MEMBER_ROLE_NAMES: set[str] = {"member", "会員", "Member"}
OBOG_ROLE_NAMES: set[str] = {"OBOG", "OB/OG", "OB-OG"}
ADMIN_ROLE_NAMES: set[str] = {"administrator", "管理者", "Administrator"}
PRE_MEMBER_ROLE_NAME: str = "pre-member"
SUB_USER_ROLE_NAMES: set[str] = {"sub垢"}


# ============================================================================
# 編集制限付きロールカテゴリ名
# ============================================================================
RESTRICTED_CATEGORY_NAMES: set[str] = {"会員情報", "学部学科", "学年"}
MEMBER_RESTRICTED_CATEGORY_NAMES: set[str] = RESTRICTED_CATEGORY_NAMES  # 後方互換用別名


# ============================================================================
# メンバーシップ種別の優先度 SQL 断片（app_role の解決に使用）
# 優先順位: admin(1) > member(2) > sub_user(3) > obog(4) > pre_member(5)
# member / sub_user / obog は同じ権限を持つが、app_role を一意に決めるため順位を分ける
# ============================================================================
MEMBERSHIP_PRIORITY_SQL: str = """
ORDER BY CASE membership_type 
	WHEN 'admin' THEN 1
	WHEN 'member' THEN 2
	WHEN 'sub_user' THEN 3
	WHEN 'obog' THEN 4
	WHEN 'pre_member' THEN 5
END
"""
