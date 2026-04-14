-- 修正 4（修正版）: インデックス・制約の確認と確立（PostgreSQL 互換性版）

-- 1. テーブル制約を確認
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints 
WHERE table_name = 'user_memberships';

-- 2. インデックスを確認（pg_indexes ビューを使用）
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'user_memberships';

-- 3. UNIQUE 制約を確認
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name = 'user_memberships' AND constraint_type = 'UNIQUE';

-- 4. 外部キー制約を確認
SELECT constraint_name, column_name
FROM information_schema.key_column_usage
WHERE table_name = 'user_memberships' AND column_name = 'discord_id';

-- 5. 必要なインデックスを作成（既存チェック付き）
CREATE INDEX IF NOT EXISTS idx_user_memberships_discord_id 
ON user_memberships(discord_id);

CREATE INDEX IF NOT EXISTS idx_user_memberships_membership_type 
ON user_memberships(membership_type);

-- 6. 確認クエリ：作成されたインデックスを表示
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'user_memberships'
ORDER BY indexname;
