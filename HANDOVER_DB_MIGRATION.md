# DB スキーマ移行 引き継ぎ書類

**作成日**: 2026年4月14日  
**対象**: AuthWebApp - user_memberships テーブル統合プロジェクト  
**ステータス**: コード実装完了 → 本番前テスト段階  
**環境**: 開発環境 → ステージング環境 → 本番環境

---

## 📖 概要

### 背景
- 既存 DB スキーマに 3 つの重複テーブル存在：member_list, admin_list, pre_member_list
- 構造が同一で、membership_type で区別するだけ
- スキーマ冗長性により運用複雑化

### 目標
- 3 つのテーブルを **user_memberships** テーブルに統合
- membership_type カラムで 'member' | 'admin' | 'pre_member' | 'obog' を管理
- app_role を計算値化（users テーブルから削除）
- B テーブルのスキーマを 25 → 12 テーブルに削減

### 期待効果
- スキーマ冗長性排除 (-3 テーブル)
- 権限管理のロジック一元化
- API 単純化
- 保守性向上

---

## 🔄 スキーマ変更内容

### テーブル構造

#### Before（現在）

```
member_list
├── id (PK)
├── discord_id (FK)
├── assigned_by
├── assigned_at
└── created_at

admin_list（同一構造）
pre_member_list（同一構造）

users
├── id
├── user_id
├── discord_id
├── app_role  ← 計算値なのに保存されている
└── created_at / updated_at
```

#### After（移行後）

```
user_memberships（統合）
├── id (PK)
├── discord_id (FK → guild_members)
├── membership_type ('member'|'admin'|'pre_member'|'obog')
├── assigned_by
├── assigned_at
└── created_at
⚠️ UNIQUE (discord_id, membership_type)

users（簡潔化）
├── id
├── user_id
├── discord_id
└── created_at / updated_at
（app_role は削除 → 計算値に）
```

### 新規リソース

#### SQL VIEW: v_users_with_app_role

```sql
CREATE VIEW v_users_with_app_role AS
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
```

**用途**: Python コードから直接 VIEW 参照、または SELECT で計算

---

## 💻 コード実装完了リスト

### Phase A: user_repository.py ✅

**修正内容:**
- `_resolve_role_from_lists()` → `_resolve_role_from_memberships()`
  - user_memberships テーブルから membership_type を クエリ
  - 優先度: admin > member > pre_member > obog > none
  
- `upsert_user()` 修正
  - INSERT/UPDATE から app_role カラム削除
  - 返り値の app_role は計算値（参考用）

- `get_user_role(user_id)` 完全書き換え
  - user_id → discord_id → user_memberships 参照
  - membership_type から app_role 計算

- `update_user_role()` 廃止
  - NotImplementedError 発生
  - app_role は計算値のため直接更新不可

**ファイル**: [backend/app/db/user_repository.py](backend/app/db/user_repository.py)

---

### Phase B-C: repository.py ✅

#### sync_member_lists() 修正

**Before:**
```python
DELETE FROM member_list, admin_list, pre_member_list
INSERT INTO member_list(...)
INSERT INTO admin_list(...)
INSERT INTO pre_member_list(...)
```

**After:**
```python
DELETE FROM user_memberships
INSERT INTO user_memberships 
  with membership_type = 'member' | 'admin' | 'pre_member'
```

#### get_member_lists() 修正

**Before:**
```python
SELECT * FROM member_list
SELECT * FROM admin_list
SELECT * FROM pre_member_list
```

**After:**
```python
SELECT * FROM user_memberships 
WHERE membership_type IN ('member','admin','pre_member','obog')
GROUP BY membership_type
```

**戻り値構造:**
```python
{
    'member_list': [...discord_ids],
    'admin_list': [...discord_ids],
    'pre_member_list': [...discord_ids],
    'obog_list': [...discord_ids],
}
```

#### ユーティリティ関数追加（14個）

```python
# membership_type 取得
get_user_membership_type(discord_id) → str
is_member(discord_id) → bool
is_admin(discord_id) → bool
is_pre_member(discord_id) → bool
is_obog(discord_id) → bool

# membership_type 管理
add_to_user_membership(discord_id, membership_type)
remove_from_user_membership(discord_id, membership_type)

# リスト取得
get_pre_member_list_v2() → list[str]

# 件数取得
get_member_user_count() → int
get_admin_user_count() → int
get_pre_member_user_count() → int
```

**ファイル**: [backend/app/db/repository.py](backend/app/db/repository.py)

---

### Phase D: reconcile.py ✅

**修正内容:**
- docstring 更新（コメント）
- "member_list/pre_member_list" → "user_memberships" 参照に統一

**動作:**
- 内部的に user_memberships から pre_member 取得
- API 応答形式は互換性維持（member_list キーで返す）

**ファイル**: [discord-bot/app/services/reconcile.py](discord-bot/app/services/reconcile.py)

---

### Phase E: members.py ✅

**add_to_member_list() 修正:**

**Before:**
```python
SELECT FROM member_list
INSERT INTO member_list
DELETE FROM pre_member_list
```

**After:**
```python
SELECT FROM user_memberships WHERE membership_type='member'
INSERT INTO user_memberships WITH membership_type='member'
DELETE FROM user_memberships WHERE membership_type='pre_member'
```

**追加:** paid_invitations INSERT 時に status='completed' を設定

**ファイル**: [backend/app/api/v1/members.py](backend/app/api/v1/members.py)

---

### Phase F: 検証済みファイル（変更不要）✅

- `backend/app/core/auth.py` - upsert_user() が app_role 返すので OK
- `backend/app/api/v1/student.py` - OTP verify で add/remove_user_to_role() 呼び出し済み
- `backend/app/api/v1/roles.py` - app_role 参照なし

---

### Phase G: SQL VIEW ✅

**ファイル**: [backend/alembic/migration_view_users_with_app_role.sql](backend/alembic/migration_view_users_with_app_role.sql)

---

## 🧪 開発環境テスト手順

### 環境構築

```bash
# 1. 開発 DB のセットアップ（Supabase 開発環境 or Docker Postgres）
docker-compose up -d postgres  # if using local Docker

# 2. 既存テーブル確認
psql -h localhost -U postgres -d authwebapp -c "\dt"

# 3. バックアップ作成
psql -h localhost -U postgres -d authwebapp << 'EOF'
CREATE TABLE member_list_backup AS SELECT * FROM member_list;
CREATE TABLE admin_list_backup AS SELECT * FROM admin_list;
CREATE TABLE pre_member_list_backup AS SELECT * FROM pre_member_list;
EOF
```

### テストシナリオ

#### テスト1: スキーマ変更検証

```bash
# 1. user_memberships テーブル作成
psql -h localhost -U postgres -d authwebapp -f backend/alembic/migration_view_users_with_app_role.sql

# 2. テーブル構造確認
psql -h localhost -U postgres -d authwebapp -c "\d user_memberships"

# 3. インデックス確認
psql -h localhost -U postgres -d authwebapp -c "\di" | grep user_memberships
```

#### テスト2: データ移行検証

```bash
# 1. 事前データ確認
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT 'member_list' as table_name, COUNT(*) FROM member_list
UNION ALL
SELECT 'admin_list', COUNT(*) FROM admin_list
UNION ALL
SELECT 'pre_member_list', COUNT(*) FROM pre_member_list;
EOF

# 2. データ移行実行（MIGRATION_PLAN_DATA_TRANSFER.md フェーズ2参照）
# 詳細は以下参照

# 3. データ検証
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT membership_type, COUNT(*) FROM user_memberships 
GROUP BY membership_type 
ORDER BY membership_type;
EOF
```

#### テスト3: Python コード検証

```bash
# 1. 開発環境で backend 起動
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# 2. テストスクリプト実行
python -c "
from app.db.user_repository import get_user_role
from app.db.repository import get_member_lists, get_user_membership_type

# Test 1: get_user_membership_type
discord_id = '123456789'  # テスト用 discord_id
role = get_user_membership_type(discord_id)
print(f'membership_type: {role}')

# Test 2: get_member_lists
lists = get_member_lists()
print(f'member_list count: {len(lists.get(\"member_list\", []))}')

# Test 3: get_user_role
user_id = 'test-user-123'
app_role = get_user_role(user_id)
print(f'app_role: {app_role}')
"
```

#### テスト4: API エンドポイント検証

```bash
# 1. 認証トークン取得
TOKEN="eyJ..."  # Supabase JWT or SHARED_SECRET

# 2. /api/v1/members テスト
curl -X GET http://localhost:8000/api/v1/members \
  -H "Authorization: Bearer $TOKEN"

# 3. /api/v1/roles テスト
curl -X GET http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer $TOKEN"

# 4. /api/v1/sync テスト
curl -X POST http://localhost:8000/api/v1/sync \
  -H "Authorization: Bearer $TOKEN"
```

#### テスト5: OTP フロー検証

```bash
# 1. OTP送信
curl -X POST http://localhost:8000/api/v1/student/otp/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_number": "1A234567",
    "name": "Test User"
  }'

# 2. OTP検証
curl -X POST http://localhost:8000/api/v1/student/otp/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'

# 3. DB 確認: user_memberships に membership_type='member' が追加されたか
psql -h localhost -U postgres -d authwebapp -c \
  "SELECT * FROM user_memberships WHERE discord_id='...' ORDER BY created_at DESC;"
```

---

## 🔄 SQL マイグレーション手順

### Phase 1: 準備（API 稼働中）

```sql
-- 1. バックアップ
CREATE TABLE member_list_backup AS SELECT * FROM member_list;
CREATE TABLE admin_list_backup AS SELECT * FROM admin_list;
CREATE TABLE pre_member_list_backup AS SELECT * FROM pre_member_list;

-- 2. user_memberships 作成
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

-- 3. インデックス
CREATE INDEX idx_user_memberships_membership_type ON user_memberships(membership_type);
CREATE INDEX idx_user_memberships_discord_id ON user_memberships(discord_id);

-- 4. 整合性確認
SELECT 'orphan_members' as check_name, COUNT(*) as count
FROM member_list ml
LEFT JOIN guild_members gm ON ml.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL
UNION ALL
SELECT 'orphan_admins', COUNT(*)
FROM admin_list al
LEFT JOIN guild_members gm ON al.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL;
```

### Phase 2: データ移行（API 停止: 5-10分間）

```sql
-- 1. DELETE 実行
DELETE FROM user_memberships;  -- 念のため既存データ削除

-- 2. member_list → user_memberships（admin との重複を避ける）
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

-- 3. admin_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT 
    al.discord_id,
    'admin' as membership_type,
    al.assigned_by,
    al.assigned_at,
    al.created_at
FROM admin_list al
ON CONFLICT (discord_id, membership_type) DO NOTHING;

-- 4. pre_member_list → user_memberships（member, admin との重複を避ける）
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

-- 5. データ検証
SELECT membership_type, COUNT(*) as count
FROM user_memberships
GROUP BY membership_type
ORDER BY membership_type;

-- 6. 1ユーザーが複数 membership_type を持つか確認（期待値: 0）
SELECT COUNT(*) as duplicates
FROM (
    SELECT discord_id, COUNT(DISTINCT membership_type) as type_count
    FROM user_memberships
    GROUP BY discord_id
    HAVING COUNT(DISTINCT membership_type) > 1
) x;
```

### Phase 3-5: スキーマ修正

```sql
-- 1. app_role カラム削除（users テーブル）
ALTER TABLE users DROP COLUMN IF EXISTS app_role;

-- 2. otp_verified / otp_verified_at 削除（student_profiles テーブル）
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified;
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified_at;

-- 3. paid_invitations 修正
ALTER TABLE paid_invitations DROP CONSTRAINT IF EXISTS "paid_invitations_discord_id_key";
ALTER TABLE paid_invitations 
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'completed' 
    CHECK (status IN ('pending', 'completed', 'expired'));
UPDATE paid_invitations SET status = 'completed' WHERE status IS NULL;
CREATE INDEX IF NOT EXISTS idx_paid_invitations_status ON paid_invitations(status);
```

### Phase 7: 旧テーブル削除

```sql
-- 1. 最終検証
SELECT 
    (SELECT COUNT(*) FROM user_memberships) as um_total,
    (SELECT COUNT(*) FROM member_list) as ml_total,
    (SELECT COUNT(*) FROM admin_list) as al_total,
    (SELECT COUNT(*) FROM pre_member_list) as pml_total;

-- 2. 削除
DROP TABLE IF EXISTS member_list_backup;
DROP TABLE IF EXISTS admin_list_backup;
DROP TABLE IF EXISTS pre_member_list_backup;
DROP TABLE IF EXISTS member_list;
DROP TABLE IF EXISTS admin_list;
DROP TABLE IF EXISTS pre_member_list;

-- 3. クリーンアップ
VACUUM FULL ANALYZE;
```

---

## 🚨 ロールバック手順

移行中に問題が発生した場合：

```sql
-- 1. user_memberships 削除
DROP TABLE IF EXISTS user_memberships;

-- 2. 旧テーブルから復元
INSERT INTO member_list SELECT * FROM member_list_backup;
INSERT INTO admin_list SELECT * FROM admin_list_backup;
INSERT INTO pre_member_list SELECT * FROM pre_member_list_backup;

-- 3. app_role カラム復元（必要な場合）
ALTER TABLE users ADD COLUMN app_role TEXT DEFAULT 'none';

-- 4. 確認
SELECT COUNT(*) FROM member_list;  -- 93 件
SELECT COUNT(*) FROM admin_list;
SELECT COUNT(*) FROM pre_member_list;
```

---

## 📋 テスト結果チェックリスト

### スキーマ検証

- [ ] user_memberships テーブル作成 OK
- [ ] UNIQUE (discord_id, membership_type) 制約 OK
- [ ] FOREIGN KEY 制約 OK
- [ ] インデックス作成 OK

### データ検証

- [ ] member_list のデータ全て移行 OK
- [ ] admin_list のデータ全て移行 OK
- [ ] pre_member_list のデータ全て移行 OK
- [ ] 重複なし（1ユーザー1つの membership_type）OK
- [ ] データ件数一致 OK

### Python コード検証

- [ ] get_user_membership_type() 動作 OK
- [ ] get_member_lists() 動作 OK
- [ ] get_user_role() 動作 OK
- [ ] add_to_user_membership() 動作 OK
- [ ] remove_from_user_membership() 動作 OK
- [ ] is_member() / is_admin() 動作 OK

### API エンドポイント検証

- [ ] GET /api/v1/members 正常応答
- [ ] POST /api/v1/members/add 正常動作
- [ ] GET /api/v1/roles 正常応答
- [ ] POST /api/v1/sync 正常動作
- [ ] POST /api/v1/student/otp/verify 正常動作

### OTP フロー検証

- [ ] OTP 送信 OK
- [ ] OTP 検証後 user_memberships に membership_type='member' 追加 OK
- [ ] role_member_assignments 更新（add member ロール）OK
- [ ] role_member_assignments 更新（remove pre_member ロール）OK

### ロールバック検証

- [ ] ロールバック実行 OK
- [ ] 旧テーブル復元 OK
- [ ] データ整合性復元 OK

---

## 📅 本番環境展開スケジュール

### ステップ1: 開発環境テスト（現在）

```
実行者: 開発チーム
所要時間: 2-3日
確認事項: 上記チェックリスト全て OK
```

### ステップ2: ステージング環境テスト

```
実行者: QA チーム
所要時間: 1日
確認事項:
  - 本番同等環境でのテスト
  - 想定ダウンタイム検証（5-10分）
  - ロールバック手順テスト
```

### ステップ3: 本番環境展開

```
実行タイミング: 非ピーク時（深夜 0:00-2:00 推奨）
ダウンタイム: 約 10-15分
実施者: DevOps チーム
手順: MIGRATION_PLAN_DATA_TRANSFER.md に従う
```

### ステップ4: 本番環境検証

```
実行者: DevOps + 開発チーム
確認事項:
  - ユーザー権限判定正常性
  - member_list / members エンドポイント正常性
  - Discord ロール同期正常性
  - OTP フロー正常性
```

---

## 📞 サポート・質問

### 問題が発生した場合

1. **開発環境での再現**
   - 同じ SQL / コードで開発環境で再現
   - ロールバック後に原因調査

2. **ホットフィックス**
   - 重要なバグは git branch で修正版作成
   - 別 release tag で本番再適用

3. **連絡先**
   - 開発チーム: [チーム Slack]
   - DBA: [DBA Slack]
   - 緊急: [緊急連絡先]

---

## 🔗 参照資料

- [DB スキーマ分析](DB_SCHEMA_ANALYSIS_AND_PROPOSAL.md)
- [マイグレーション計画](MIGRATION_PLAN_DATA_TRANSFER.md)
- [実装ガイド](IMPLEMENTATION_GUIDE_AFTER_MIGRATION.md)
- [テストガイド](docs/TEST_GUIDE.md)

---

**最終確認**: 
- [ ] 開発環境テスト完了
- [ ] ステージング環境テスト完了
- [ ] 本番環境展開実施
- [ ] 本番環境検証完了

