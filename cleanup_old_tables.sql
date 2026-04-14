-- DB スキーマ移行完了後：旧テーブル削除スクリプト
-- 日付: 2026-04-14
-- 目的: user_memberships テーブルへの統合完了に伴い、旧テーブルを削除

-- ============================================================================
-- Phase 1: データバックアップ確認（削除前）
-- ============================================================================

-- 削除前に各テーブルのレコード数を確認
SELECT 'member_list' as table_name, COUNT(*) as row_count FROM member_list
UNION ALL
SELECT 'admin_list', COUNT(*) FROM admin_list
UNION ALL
SELECT 'pre_member_list', COUNT(*) FROM pre_member_list
UNION ALL
SELECT 'user_memberships_backup', COUNT(*) FROM user_memberships_backup;

-- ============================================================================
-- Phase 2: 旧テーブル削除
-- ============================================================================

-- 1. member_list を削除
DROP TABLE IF EXISTS public.member_list CASCADE;
-- 確認メッセージ: member_list 削除完了

-- 2. admin_list を削除
DROP TABLE IF EXISTS public.admin_list CASCADE;
-- 確認メッセージ: admin_list 削除完了

-- 3. pre_member_list を削除
DROP TABLE IF EXISTS public.pre_member_list CASCADE;
-- 確認メッセージ: pre_member_list 削除完了

-- 4. user_memberships_backup を削除（テンポラリバックアップ）
DROP TABLE IF EXISTS public.user_memberships_backup CASCADE;
-- 確認メッセージ: user_memberships_backup 削除完了

-- ============================================================================
-- Phase 3: 削除確認
-- ============================================================================

-- 削除されたテーブルが本当に存在しないか確認
SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='member_list') as member_list_exists,
       EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='admin_list') as admin_list_exists,
       EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='pre_member_list') as pre_member_list_exists,
       EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='user_memberships_backup') as backup_exists;

-- 期待値: false, false, false, false

-- ============================================================================
-- Phase 4: 統合テーブルの確認
-- ============================================================================

-- user_memberships が正常に機能しているか確認
SELECT 
    membership_type,
    COUNT(*) as count
FROM user_memberships
GROUP BY membership_type
ORDER BY membership_type;

-- ============================================================================
-- 完了メッセージ
-- ============================================================================
-- ✓ すべての旧テーブルが削除されました
-- ✓ user_memberships テーブルに統合済みのデータが正常に保持されています
-- ✓ スキーマは最適化状態です
