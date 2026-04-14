# DB スキーマ移行手順書：既存データ から 新スキーマへ

**作成日**: 2026年4月14日  
**対象**: member_list（93件） + admin_list + pre_member_list → user_memberships 統合  
**想定ダウンタイム**: 5-10分（非ピーク時推奨）

---

## 📋 移行フェーズと処理内容

### **フェーズ1: 準備（ダウンタイム前）**

#### 1-1. バックアップ作成

```sql
-- 既存リスト系テーブルのバックアップ
CREATE TABLE IF NOT EXISTS member_list_backup AS
SELECT * FROM member_list;

CREATE TABLE IF NOT EXISTS admin_list_backup AS
SELECT * FROM admin_list;

CREATE TABLE IF NOT EXISTS pre_member_list_backup AS
SELECT * FROM pre_member_list;

-- 確認
SELECT COUNT(*) as member_list_count FROM member_list_backup;  -- 93
SELECT COUNT(*) as admin_list_count FROM admin_list_backup;
SELECT COUNT(*) as pre_member_list_count FROM pre_member_list_backup;
```

#### 1-2. 新テーブル作成

```sql
-- user_memberships テーブル作成
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

-- インデックス作成（クエリ高速化）
CREATE INDEX idx_user_memberships_membership_type ON user_memberships(membership_type);
CREATE INDEX idx_user_memberships_discord_id ON user_memberships(discord_id);
```

#### 1-3. guild_members 関連の整合性確認

```sql
-- guild_members が存在しないのに member_list に登録されているユーザーを検出
SELECT 
    'missing_in_guild_members' as issue,
    ml.discord_id,
    COUNT(*) as count
FROM member_list ml
LEFT JOIN guild_members gm ON ml.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL
GROUP BY ml.discord_id;

-- 同様に admin_list, pre_member_list
SELECT 
    'missing_in_guild_members' as issue,
    al.discord_id,
    COUNT(*) as count
FROM admin_list al
LEFT JOIN guild_members gm ON al.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL
GROUP BY al.discord_id;

SELECT 
    'missing_in_guild_members' as issue,
    pml.discord_id,
    COUNT(*) as count
FROM pre_member_list pml
LEFT JOIN guild_members gm ON pml.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL
GROUP BY pml.discord_id;
```

**⚠️ 問題が見つかった場合の対応**:
```sql
-- guild_members に不足ユーザーを追加（Discord API から取得した情報を使用）
INSERT INTO guild_members (discord_id, username, display_name, avatar, updated_at)
VALUES 
    ('1234567890', 'username', 'Display Name', 'avatar_url', now())
ON CONFLICT DO NOTHING;
```

---

### **フェーズ2: データマイグレーション（ダウンタイム中）**

#### 2-1. 重複チェック

複数のリストに同時登録されているユーザーを検出：

```sql
-- 複合登録検出
WITH all_users AS (
    SELECT discord_id, 'member' as type FROM member_list
    UNION ALL
    SELECT discord_id, 'admin' FROM admin_list
    UNION ALL
    SELECT discord_id, 'pre_member' FROM pre_member_list
)
SELECT discord_id, COUNT(DISTINCT type) as type_count, STRING_AGG(type, ',') as types
FROM all_users
GROUP BY discord_id
HAVING COUNT(DISTINCT type) > 1
ORDER BY type_count DESC;
```

**重複の解決ルール**:
```
優先順位（高 → 低）:
1. admin > member > pre_member > obog
2. 同じ type なら最新の assigned_at を保持

例: admin_list に存在 + member_list に存在 
    → admin のみを user_memberships に登録
    → member は登録しない（admin が member より上位）
```

#### 2-2. member_list → user_memberships

```sql
-- member_list から user_memberships に Insert
-- ただし admin 重複を避ける
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

-- 確認
SELECT COUNT(*) as inserted FROM user_memberships WHERE membership_type = 'member';
-- 期待値: member_list から admin 重複分を除いた数
```

#### 2-3. admin_list → user_memberships

```sql
-- admin_list から user_memberships に Insert
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT 
    al.discord_id,
    'admin' as membership_type,
    al.assigned_by,
    al.assigned_at,
    al.created_at
FROM admin_list al
ON CONFLICT (discord_id, membership_type) DO NOTHING;

SELECT COUNT(*) as inserted FROM user_memberships WHERE membership_type = 'admin';
```

#### 2-4. pre_member_list → user_memberships

```sql
-- pre_member_list から user_memberships に Insert
-- ただし member, admin 重複を避ける
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

SELECT COUNT(*) as inserted FROM user_memberships WHERE membership_type = 'pre_member';
```

#### 2-5. データ検証

```sql
-- 検証1: 総レコード数
SELECT 
    'member_list' as source, COUNT(*) as count FROM member_list
UNION ALL
SELECT 'admin_list', COUNT(*) FROM admin_list
UNION ALL
SELECT 'pre_member_list', COUNT(*) FROM pre_member_list
UNION ALL
SELECT 'user_memberships', COUNT(*) FROM user_memberships;

-- 検証2: membership_type 別の件数
SELECT membership_type, COUNT(*) as count
FROM user_memberships
GROUP BY membership_type
ORDER BY count DESC;

-- 検証3: 1つのユーザーが複数 membership_type を持つ場合（期待値: 0）
SELECT discord_id, COUNT(DISTINCT membership_type) as type_count
FROM user_memberships
GROUP BY discord_id
HAVING COUNT(DISTINCT membership_type) > 1;

-- 検証4: guild_members に存在しないレコード（FK 制約で防止されるので不要だが念のため）
SELECT COUNT(*) as orphan_count
FROM user_memberships um
LEFT JOIN guild_members gm ON um.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL;
```

---

### **フェーズ3: users テーブル修正**

#### 3-1. app_role 削除準備

```sql
-- 確認: 現在の app_role 値の分布
SELECT app_role, COUNT(*) as count
FROM users
GROUP BY app_role;

-- 計算値として保存する app_role の生成ロジック（Python で実装予定）
-- SELECT user_id, CASE 
--   WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id=users.discord_id AND membership_type='admin')
--     THEN 'admin'
--   WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id=users.discord_id AND membership_type='member')
--     THEN 'member'
--   WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id=users.discord_id AND membership_type='pre_member')
--     THEN 'pre_member'
--   ELSE 'none'
-- END as calculated_app_role
-- FROM users;
```

#### 3-2. app_role カラム削除

```sql
-- users テーブル対象スキーマは以下の通り:
-- id, user_id, discord_id, app_role, created_at, updated_at

-- app_role を削除する前に、Python コード内で
-- user_repository の app_role 計算ロジックが実装されていることを確認

-- 確認後に実行:
ALTER TABLE users DROP COLUMN app_role;

-- 削除後のスキーマ:
-- id, user_id, discord_id, created_at, updated_at
```

---

### **フェーズ4: student_profiles テーブル修正**

#### 4-1. otp_verified 状態を確認

```sql
-- 現在の otp_verified フラグの分布
SELECT 
    otp_verified,
    COUNT(*) as count,
    COUNT(CASE WHEN otp_verified_at IS NOT NULL THEN 1 END) as with_timestamp
FROM student_profiles
GROUP BY otp_verified;

-- 検証: otp_verified = FALSE でも otp_verified_at が NULL でない場合（データ不整合）
SELECT COUNT(*) as inconsistent_count
FROM student_profiles
WHERE otp_verified = FALSE AND otp_verified_at IS NOT NULL;
```

#### 4-2. otp_codes との同期確認

```sql
-- student_profiles の discord_id と otp_codes の verified_at 状態を比較
SELECT 
    sp.discord_id,
    sp.otp_verified,
    sp.otp_verified_at,
    oc.verified_at as otp_codes_verified_at,
    CASE 
        WHEN sp.otp_verified AND oc.verified_at IS NOT NULL THEN 'MATCH'
        WHEN NOT sp.otp_verified AND oc.verified_at IS NULL THEN 'MATCH'
        ELSE 'MISMATCH'
    END as status
FROM student_profiles sp
LEFT JOIN otp_codes oc ON sp.discord_id = (
    SELECT jr.email FROM join_requests jr WHERE oc.join_request_id = jr.id
)
ORDER BY status;

-- 不一致を手動で確認し、修正が必要な場合は対応
```

#### 4-3. otp_verified カラム削除

```sql
-- verification state は otp_codes.verified_at から取得するため削除
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified;
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified_at;

-- 削除後のスキーマ:
-- id, discord_id, student_number, name, furigana, department, 
-- gender, phone, email_aoyama, email_verified, email_verified_at,
-- profile_submitted_at, created_at, updated_at
```

---

### **フェーズ5: paid_invitations テーブル修正**

#### 5-1. 既存レコードを確認

```sql
-- 現在の paid_invitations の状態
SELECT 
    COUNT(*) as total_count,
    COUNT(DISTINCT discord_id) as unique_discord_ids,
    MAX(assigned_at) as latest_assignment,
    COUNT(DISTINCT assigned_by) as unique_admins
FROM paid_invitations;

-- Discord ID の重複を検出（現在の UNIQUE 制約で不可能だが念のため）
SELECT discord_id, COUNT(*) as count
FROM paid_invitations
GROUP BY discord_id
HAVING COUNT(*) > 1;
```

#### 5-2. UNIQUE 制約削除と status カラム追加

```sql
-- UNIQUE 制約削除（複数バージョン対応）
ALTER TABLE paid_invitations DROP CONSTRAINT IF EXISTS "paid_invitations_discord_id_key";

-- status カラム追加
ALTER TABLE paid_invitations 
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'completed' 
    CHECK (status IN ('pending', 'completed', 'expired'));

-- 既存レコードのステータスを 'completed' にセット（支払い済みだから）
UPDATE paid_invitations SET status = 'completed' WHERE status IS NULL;

-- インデックス追加（ステータスで検索しやすく）
CREATE INDEX IF NOT EXISTS idx_paid_invitations_status ON paid_invitations(status);
CREATE INDEX IF NOT EXISTS idx_paid_invitations_discord_id_status 
    ON paid_invitations(discord_id, status);
```

#### 5-3. user_memberships との関連確認

```sql
-- paid_invitations と user_memberships の関連確認
-- pre_member で支払い済み → member へのプロモーション時に参照
SELECT 
    pi.discord_id,
    pi.status,
    STRING_AGG(DISTINCT um.membership_type, ',') as membership_types
FROM paid_invitations pi
LEFT JOIN user_memberships um ON pi.discord_id = um.discord_id
GROUP BY pi.discord_id, pi.status;
```

---

### **フェーズ6: OTP フロー の統一（オプション）**

#### 6-1. otp_records と otp_codes の並行状態を確認

```sql
-- 現在のレコード数
SELECT 
    'otp_records' as table_name, COUNT(*) as count FROM otp_records
UNION ALL
SELECT 'otp_codes', COUNT(*) FROM otp_codes;

-- 対象ユーザーが重複しているか？
SELECT 
    'both' as status,
    COUNT(DISTINCT or_discord_id) as both_count
FROM (
    SELECT DISTINCT discord_id as or_discord_id FROM otp_records
) or_ids
INNER JOIN (
    SELECT DISTINCT jr.email FROM otp_codes oc
    JOIN join_requests jr ON oc.join_request_id = jr.id
) oc_emails
ON or_ids.or_discord_id IN (SELECT discord_id FROM otp_records WHERE email_aoyama = oc_emails.email);
```

#### 6-2. otp_records → otp_codes への移行（段階的）

```sql
-- オプション1: otp_records を保持（旧フロー互換）
-- → そのまま parallel 運用

-- オプション2: otp_records を削除（新フロー完全移行）
-- → 以下を実行
DELETE FROM otp_records WHERE verified = FALSE;  -- 未検証のみ削除
DELETE FROM otp_records;  -- 全削除
DROP TABLE otp_records;
```

**推奨**: 段階的に otp_records 削除（複雑な migration なため）

---

### **フェーズ7: 旧テーブル削除**

#### 7-1. 削除前の最終確認

```sql
-- データ整合性の最終チェック
SELECT 
    (SELECT COUNT(*) FROM user_memberships) as um_total,
    (SELECT COUNT(*) FROM member_list) as ml_total,
    (SELECT COUNT(*) FROM admin_list) as al_total,
    (SELECT COUNT(*) FROM pre_member_list) as pml_total;

-- 期待値: um_total ≥ ml_total + al_total + pml_total（重複除去のため）
```

#### 7-2. テーブル削除

```sql
-- ⚠️ バックアップ確認後に実行

-- 外部キー制約を持つテーブルから削除開始
-- 参照元が存在しないか確認
SELECT * FROM information_schema.referential_constraints 
WHERE constraint_schema = 'public' 
AND (table_name IN ('member_list', 'admin_list', 'pre_member_list') 
     OR referenced_table_name IN ('member_list', 'admin_list', 'pre_member_list'));

-- 削除実行
DROP TABLE IF EXISTS member_list_backup;
DROP TABLE IF EXISTS admin_list_backup;
DROP TABLE IF EXISTS pre_member_list_backup;
DROP TABLE IF EXISTS member_list;
DROP TABLE IF EXISTS admin_list;
DROP TABLE IF EXISTS pre_member_list;

-- DB クリーンアップ
VACUUM FULL ANALYZE;
```

---

## 🔄 ロールバック手順

何か問題が発生した場合：

```sql
-- ロールバック1: user_memberships を削除して旧テーブルに戻す
DROP TABLE IF EXISTS user_memberships;

-- ロールバック2: バックアップから復元
INSERT INTO member_list SELECT * FROM member_list_backup;
INSERT INTO admin_list SELECT * FROM admin_list_backup;
INSERT INTO pre_member_list SELECT * FROM pre_member_list_backup;

-- ロールバック3: app_role カラムを戻す（フェーズ3 後の場合）
ALTER TABLE users ADD COLUMN app_role TEXT DEFAULT 'none';
UPDATE users SET app_role = <calculate from old logic>;

-- ロールバック確認
SELECT COUNT(*) FROM member_list;  -- 93
SELECT COUNT(*) FROM admin_list;
SELECT COUNT(*) FROM pre_member_list;
```

---

## 📊 実行順序の推奨スケジュール

### **ステップ1: オフピーク時（0:00-2:00 など）**

```
1. フェーズ1 実施（バックアップ、新テーブル作成）
   - ダウンタイム不要
   - API は稼働中

2. フェーズ2 実施（データマイグレーション）
   - API を一時停止（5-10分）
   - user_memberships に全データを INSERT
   - 検証後に commit

3. フェーズ3-5 実施（スキーマ修正）
   - app_role 削除、otp_verified 削除、status 追加
   - ダウンタイム: 追加 2-3分

4. フェーズ7 実施（旧テーブル削除）
   - 旧テーブル削除確認後
   - ダウンタイム: 追加 1分
   
総ダウンタイム: 約 10-15分
```

### **ステップ2: コード変更（次の release cycle）**

```
1. user_repository.py に app_role 計算ロジック追加
2. repository.py の sync_member_lists() を user_memberships に修正
3. reconcile.py の pre_member 読込元を user_memberships に修正
4. 他の API で member_list → user_memberships 参照に変更
5. テスト実施（unit + integration）
6. ステージング環境でテスト
7. 本番環境で deploy
```

---

## ✅ チェックリスト

### 移行前

- [ ] バックアップ確認
- [ ] guild_members との整合性確認
- [ ] 重複ユーザーの解決ルール決定
- [ ] ロールバック手順の確認
- [ ] 本番環境以外でドライラン実施

### 移行中

- [ ] API 停止（メンテナンスモード）
- [ ] データマイグレーション実行
- [ ] 検証クエリ実行（全て OK）
- [ ] スキーマ修正実行
- [ ] 旧テーブル削除
- [ ] API 再開

### 移行後

- [ ] ユーザーの権限判定正常性確認
- [ ] member_list クエリ実行正常性確認
- [ ] ログ監視（エラー増加なし）
- [ ] コード commit + code review
- [ ] 次の release に含める

---

## 📝 SQL 実行順序（統合スクリプト）

以下のコマンドで一括実行可能（テスト環境推奨）：

```bash
# ステージング環境でテスト
psql $DATABASE_URL << 'EOF'
-- フェーズ1: バックアップ + 新テーブル作成
\i migration_phase1_backup_and_create.sql

-- フェーズ2: データマイグレーション
\i migration_phase2_data_transfer.sql

-- フェーズ3-5: スキーマ修正
\i migration_phase3_5_schema_cleanup.sql

-- 検証
\i migration_validate_all.sql
EOF

# 本番環境で実行（要承認）
psql $PRODUCTION_DATABASE_URL << 'EOF'
-- 上記と同じセクション
EOF
```

