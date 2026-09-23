"""役割: PostgreSQLへの永続化処理（ファサードモジュール）

NOTE: このモジュールは後方互換性のためのファサード（再エクスポート）です。
既存のコードを壊さずに段階的リファクタリングを行うため、全公開関数を再エクスポートしています。
新規コードでは以下のドメイン別モジュールを直接参照してください:
- app.db.connection: DB接続管理・ログユーティリティ
- app.db.schema: DDL/マイグレーション (init_db)
- app.db.manifest_repository: ロールマニフェスト・カテゴリ
- app.db.guild_repository: ギルドメンバー・ロール割り当て
- app.db.membership_repository: メンバーシップ・参加申請
- app.db.otp_repository: OTP認証・フォーム申請
"""

from __future__ import annotations

# 1. DB接続管理 & ユーティリティ
from app.db.connection import (
	DATABASE_URL,
	_connect,
	_log_db_access,
	_should_log_to_stdout,
)

# 2. DDL & マイグレーション
from app.db.schema import (
	init_db,
)

# 3. ロールマニフェスト関連
from app.db.manifest_repository import (
	fetch_manifest,
	patch_manifest_db,
	replace_roles_from_discord,
	save_manifest,
	update_role_id,
)

# 4. ギルドメンバー・ロール割り当て関連
from app.db.guild_repository import (
	add_user_to_role,
	batch_update_user_roles,
	clear_all_role_assignments,
	fetch_guild_members,
	fetch_role_assignments,
	fetch_role_assignments_for_user,
	remove_user_from_role,
	save_guild_members,
	save_role_assignments,
)

# 5. メンバーシップ関連
from app.db.membership_repository import (
	add_to_member_list,
	add_to_user_membership,
	cleanup_expired_prospective_members,
	expiry_from_assigned_at,
	get_admin_user_count,
	get_member_lists,
	get_member_user_count,
	get_membership_count,
	get_pre_member_list_v2,
	get_pre_member_list_with_users,
	get_pre_member_user_count,
	get_user_membership_type,
	has_membership,
	is_admin,
	is_member,
	is_obog,
	is_pre_member,
	is_prospective_form_open,
	register_paid_invitation,
	register_pre_member,
	remove_from_user_membership,
	sync_member_lists,
)

# 6. OTP・参加申請関連
from app.db.otp_repository import (
	create_join_request,
	create_otp_code,
	get_join_request,
	save_member_survey_response,
	verify_otp,
)

# 7. 学生登録・学生OTP関連
from app.db.student_repository import (
	create_otp_record,
	get_latest_otp,
	get_latest_verified_otp,
	get_student_profile,
	get_student_profile as _get_student_profile,
	increment_otp_attempt,
	is_paid_invitation,
	mark_otp_verified,
	upsert_student_profile_and_promote,
)

__all__ = [
	"DATABASE_URL",
	"_connect",
	"_log_db_access",
	"_should_log_to_stdout",
	"init_db",
	"fetch_manifest",
	"save_manifest",
	"replace_roles_from_discord",
	"update_role_id",
	"patch_manifest_db",
	"save_guild_members",
	"save_role_assignments",
	"add_user_to_role",
	"batch_update_user_roles",
	"remove_user_from_role",
	"clear_all_role_assignments",
	"fetch_guild_members",
	"fetch_role_assignments",
	"fetch_role_assignments_for_user",
	"is_prospective_form_open",
	"sync_member_lists",
	"get_member_lists",
	"get_user_membership_type",
	"is_member",
	"is_admin",
	"is_pre_member",
	"is_obog",
	"has_membership",
	"add_to_user_membership",
	"remove_from_user_membership",
	"get_pre_member_list_v2",
	"get_member_user_count",
	"get_admin_user_count",
	"get_pre_member_user_count",
	"get_membership_count",
	"register_pre_member",
	"expiry_from_assigned_at",
	"cleanup_expired_prospective_members",
	"get_pre_member_list_with_users",
	"add_to_member_list",
	"register_paid_invitation",
	"create_join_request",
	"create_otp_code",
	"verify_otp",
	"get_join_request",
	"save_member_survey_response",
	"create_otp_record",
	"get_latest_otp",
	"get_latest_verified_otp",
	"get_student_profile",
	"increment_otp_attempt",
	"is_paid_invitation",
	"mark_otp_verified",
	"upsert_student_profile_and_promote",
]
