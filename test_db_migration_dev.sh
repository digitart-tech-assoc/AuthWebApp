#!/bin/bash
# DB スキーマ移行：開発環境テストスクリプト
# 用途: 開発環境で移行手順の全テストを自動実行

set -e

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-authwebapp}"
DB_PASSWORD="${DB_PASSWORD:-}"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# DB 接続確認
test_db_connection() {
    log_info "DB 接続確認..."
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
        log_success "DB 接続 OK"
        return 0
    else
        log_error "DB 接続失敗"
        return 1
    fi
}

# バックアップ作成
create_backup() {
    log_info "バックアップ作成..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
CREATE TABLE IF NOT EXISTS member_list_backup AS SELECT * FROM member_list;
CREATE TABLE IF NOT EXISTS admin_list_backup AS SELECT * FROM admin_list;
CREATE TABLE IF NOT EXISTS pre_member_list_backup AS SELECT * FROM pre_member_list;
EOF
    log_success "バックアップ作成 OK"
}

# 既存データ確認
show_before_data() {
    log_info "移行前のデータ件数..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
SELECT 'member_list' as table_name, COUNT(*) as count FROM member_list
UNION ALL
SELECT 'admin_list', COUNT(*) FROM admin_list
UNION ALL
SELECT 'pre_member_list', COUNT(*) FROM pre_member_list;
EOF
}

# user_memberships テーブル作成
create_user_memberships_table() {
    log_info "user_memberships テーブル作成..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
CREATE TABLE IF NOT EXISTS user_memberships (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT NOT NULL,
    membership_type TEXT NOT NULL CHECK (membership_type IN ('member', 'admin', 'pre_member', 'obog')),
    assigned_by TEXT,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (discord_id, membership_type),
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_memberships_membership_type ON user_memberships(membership_type);
CREATE INDEX IF NOT EXISTS idx_user_memberships_discord_id ON user_memberships(discord_id);
EOF
    log_success "user_memberships テーブル作成 OK"
}

# データ整合性確認
check_integrity() {
    log_info "guild_members との整合性確認..."
    ORPHAN_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM (
    SELECT 'orphan_members' FROM member_list ml
    LEFT JOIN guild_members gm ON ml.discord_id = gm.discord_id
    WHERE gm.discord_id IS NULL
    UNION ALL
    SELECT 'orphan_admins' FROM admin_list al
    LEFT JOIN guild_members gm ON al.discord_id = gm.discord_id
    WHERE gm.discord_id IS NULL
) x;
" | tr -d ' ')
    
    if [ "$ORPHAN_COUNT" -gt 0 ]; then
        log_warning "孤立したレコード検出: $ORPHAN_COUNT 件"
    else
        log_success "整合性チェック OK （孤立レコード: 0 件）"
    fi
}

# データ移行
migrate_data() {
    log_info "データ移行実行..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
-- member_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT 
    ml.discord_id,
    'member' as membership_type,
    ml.assigned_by,
    ml.assigned_at,
    ml.created_at
FROM member_list ml
WHERE NOT EXISTS (
    SELECT 1 FROM admin_list al WHERE al.discord_id = ml.discord_id
)
ON CONFLICT (discord_id, membership_type) DO NOTHING;

-- admin_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT 
    al.discord_id,
    'admin' as membership_type,
    al.assigned_by,
    al.assigned_at,
    al.created_at
FROM admin_list al
ON CONFLICT (discord_id, membership_type) DO NOTHING;

-- pre_member_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT 
    pml.discord_id,
    'pre_member' as membership_type,
    pml.assigned_by,
    pml.assigned_at,
    pml.created_at
FROM pre_member_list pml
WHERE NOT EXISTS (
    SELECT 1 FROM member_list ml WHERE ml.discord_id = pml.discord_id
)
AND NOT EXISTS (
    SELECT 1 FROM admin_list al WHERE al.discord_id = pml.discord_id
)
ON CONFLICT (discord_id, membership_type) DO NOTHING;
EOF
    log_success "データ移行 OK"
}

# データ検証
validate_data() {
    log_info "移行後のデータ検証..."
    
    # 件数確認
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
SELECT membership_type, COUNT(*) as count
FROM user_memberships
GROUP BY membership_type
ORDER BY membership_type;
EOF

    # 重複チェック
    DUPLICATE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM (
    SELECT discord_id, COUNT(DISTINCT membership_type) as type_count
    FROM user_memberships
    GROUP BY discord_id
    HAVING COUNT(DISTINCT membership_type) > 1
) x;
" | tr -d ' ')

    if [ "$DUPLICATE_COUNT" -gt 0 ]; then
        log_error "重複ユーザー検出: $DUPLICATE_COUNT 件"
        return 1
    else
        log_success "データ検証 OK （重複: 0 件）"
        return 0
    fi
}

# SQL VIEW 作成
create_view() {
    log_info "SQL VIEW 作成（v_users_with_app_role）..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
CREATE OR REPLACE VIEW v_users_with_app_role AS
SELECT 
    u.id,
    u.user_id,
    u.discord_id,
    CASE 
        WHEN EXISTS (SELECT 1 FROM user_memberships 
                     WHERE discord_id = u.discord_id 
                     AND membership_type = 'admin')
            THEN 'admin'
        WHEN EXISTS (SELECT 1 FROM user_memberships 
                     WHERE discord_id = u.discord_id 
                     AND membership_type = 'member')
            THEN 'member'
        WHEN EXISTS (SELECT 1 FROM user_memberships 
                     WHERE discord_id = u.discord_id 
                     AND membership_type = 'pre_member')
            THEN 'pre_member'
        WHEN EXISTS (SELECT 1 FROM user_memberships 
                     WHERE discord_id = u.discord_id 
                     AND membership_type = 'obog')
            THEN 'obog'
        ELSE 'none'
    END as app_role
FROM users u;
EOF
    log_success "SQL VIEW 作成 OK"
}

# スキーマ修正
apply_schema_changes() {
    log_info "スキーマ修正実行..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
-- app_role カラム削除
ALTER TABLE users DROP COLUMN IF EXISTS app_role;

-- otp_verified カラム削除
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified;
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified_at;

-- paid_invitations 修正
ALTER TABLE paid_invitations DROP CONSTRAINT IF EXISTS "paid_invitations_discord_id_key";
ALTER TABLE paid_invitations 
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'completed' 
    CHECK (status IN ('pending', 'completed', 'expired'));
UPDATE paid_invitations SET status = 'completed' WHERE status IS NULL;
CREATE INDEX IF NOT EXISTS idx_paid_invitations_status ON paid_invitations(status);
EOF
    log_success "スキーマ修正 OK"
}

# ロールバック
rollback_changes() {
    log_warning "ロールバック実行..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
DROP TABLE IF EXISTS user_memberships;

INSERT INTO member_list SELECT * FROM member_list_backup;
INSERT INTO admin_list SELECT * FROM admin_list_backup;
INSERT INTO pre_member_list SELECT * FROM pre_member_list_backup;

ALTER TABLE users ADD COLUMN app_role TEXT DEFAULT 'none';
EOF
    log_success "ロールバック OK"
}

# メイン処理
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}DB スキーマ移行テスト（開発環境）${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # 1. DB 接続確認
    test_db_connection || exit 1
    echo ""
    
    # 2. 既存データ確認
    show_before_data
    echo ""
    
    # 3. バックアップ作成
    create_backup
    echo ""
    
    # 4. user_memberships テーブル作成
    create_user_memberships_table
    echo ""
    
    # 5. 整合性確認
    check_integrity
    echo ""
    
    # 6. データ移行
    migrate_data
    echo ""
    
    # 7. データ検証
    if ! validate_data; then
        log_error "データ検証失敗。ロールバック実行..."
        rollback_changes
        exit 1
    fi
    echo ""
    
    # 8. SQL VIEW 作成
    create_view
    echo ""
    
    # 9. スキーマ修正
    apply_schema_changes
    echo ""
    
    # 完了
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}テスト完了！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    log_info "次のステップ:"
    echo "  1. Python コード検証（backend 起動）"
    echo "  2. API エンドポイント検証"
    echo "  3. OTP フロー検証"
    echo "  4. 全テスト完了後: ステージング環境テスト"
}

# スクリプト実行
if [ "$1" = "--rollback" ]; then
    log_warning "ロールバックモード"
    test_db_connection || exit 1
    rollback_changes
else
    main
fi
