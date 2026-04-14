# 開発環境テスト実行ガイド

**目的**: DB スキーマ移行の検証を本番展開前に開発環境で完全テスト  
**所要時間**: 約 1-2 時間  
**環境**: 開発用 PostgreSQL + Python backend

---

## 前提条件

```bash
# 1. Docker 環境確認
docker ps  # または docker-compose ps

# 2. PostgreSQL が稼働していることを確認
docker-compose logs postgres  # ログ確認

# 3. Python 環境確認
python --version  # 3.9+ 推奨
pip list | grep -i psycopg  # psycopg ドライバ確認
```

---

## ステップ 1: SQL マイグレーション（自動テスト）

### 1-1. テストスクリプト実行

```bash
# リポジトリ直下に移動
cd /home/chrom/develops/AuthWebApp

# スクリプトに実行権限付与
chmod +x test_db_migration_dev.sh

# テスト実行
./test_db_migration_dev.sh
```

**期待される出力:**
```
========================================
DB スキーマ移行テスト（開発環境）
========================================

[INFO] DB 接続確認...
[SUCCESS] DB 接続 OK

[INFO] 移行前のデータ件数...
 table_name  | count
─────────────┼───────
 member_list |    93
 admin_list  |     5
 pre_member  |    12

...

[SUCCESS] テスト完了！
========================================
```

### 1-2. トラブルシューティング

**エラー: "DB 接続失敗"**
```bash
# PostgreSQL ログ确认
docker-compose logs postgres

# PostgreSQL 再起動
docker-compose down postgres
docker-compose up -d postgres
sleep 3  # 起動待機
./test_db_migration_dev.sh
```

**エラー: "孤立したレコード検出"**
```bash
# guild_members に不足している discord_id を確認
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT ul.discord_id, ul.table_name
FROM (
    SELECT DISTINCT discord_id, 'member_list' as table_name FROM member_list
    UNION ALL
    SELECT DISTINCT discord_id, 'admin_list' FROM admin_list
    UNION ALL
    SELECT DISTINCT discord_id, 'pre_member_list' FROM pre_member_list
) ul
LEFT JOIN guild_members gm ON ul.discord_id = gm.discord_id
WHERE gm.discord_id IS NULL;
EOF

# 不足している discord_id を guild_members に追加
psql -h localhost -U postgres -d authwebapp << 'EOF'
INSERT INTO guild_members (discord_id, username, display_name)
VALUES ('123456789', 'unknown_user', 'Unknown User')
ON CONFLICT DO NOTHING;
EOF
```

### 1-3. ロールバック（問題時）

```bash
# ロールバックモード実行
./test_db_migration_dev.sh --rollback

# 旧テーブルが復元されたか確認
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT COUNT(*) FROM member_list;  -- 93 が返ってこるはず
EOF
```

---

## ステップ 2: Python コード検証

### 2-1. テストスクリプト実行

```bash
# Python 開発環境セットアップ
cd backend

# 仮想環境構築（未済の場合）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows

# 依存パッケージインストール
pip install -r requirements.txt

# テストスクリプト実行
cd ..
python test_python_code_migration_dev.py
```

**期待される出力:**
```
============================================================
DB スキーマ移行：Python コード検証
============================================================

[Test 1] ユーティリティ関数の存在確認...
✓ ユーティリティ関数インポート OK

[Test 2] user_repository の関数確認...
✓ user_repository 関数インポート OK

[Test 3] DB 接続確認...
✓ DB 接続 OK

[Test 4] user_memberships テーブル確認...
  テーブル構造:
    - id: text
    - discord_id: text
    - membership_type: text
    - assigned_by: text
    - assigned_at: timestamp with time zone
    - created_at: timestamp with time zone
✓ JSON user_memberships テーブル OK

[Test 5] users テーブルから app_role カラム削除確認...
✓ app_role カラム削除確認 OK（既に削除済み）

[Test 6] 関数の動作テスト...
  - get_user_membership_type()... ✓ (結果: 'none')
  - is_member()... ✓ (結果: False)
  - is_admin()... ✓ (結果: False)
  - add_to_user_membership()... ✓
  - get_user_role()... ✓ (結果: 'none')
  - get_member_lists()... ✓ (member: 93, admin: 5)
✓ 関数テスト OK

============================================================
✓ Python コード検証完了！
============================================================

次のステップ:
1. backend を起動: python -m uvicorn app.main:app --reload
2. API エンドポイント検証
3. OTP フロー検証
4. すべて OK なら ステージング環境テスト
```

---

## ステップ 3: Backend API 検証

### 3-1. Backend 起動

```bash
cd backend

# uvicorn で起動
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 別ターミナルで進行
```

**ログ確認:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 3-2. API エンドポイント検証

```bash
# テスト用トークン取得（Supabase 環境の場合）
# または開発用 SHARED_SECRET を使用
TOKEN="dev-secret"

# Test 1: GET /api/v1/members - member リスト取得
curl -X GET http://localhost:8000/api/v1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# 期待される応答:
# {
#   "members": [
#     "123456789",
#     "987654321",
#     ...
#   ]
# }

# Test 2: GET /api/v1/roles - 全ロール情報取得
curl -X GET http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer $TOKEN"

# Test 3: POST /api/v1/sync - member_list 同期
curl -X POST http://localhost:8000/api/v1/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# 期待される応答:
# {
#   "synced": true,
#   "message": "Synced successfully"
# }
```

### 3-3. ログ確認

```bash
# Backend ターミナルのログを確認
# エラーが無いか確認
# user_memberships へのクエリが成功しているか確認

# SQL ログを有効にする場合（環境変数設定）
export SQLALCHEMY_ECHO=1
python -m uvicorn app.main:app --reload
```

---

## ステップ 4: OTP フロー検証

### 4-1. OTP 送信テスト

```bash
# OTP 送信
curl -X POST http://localhost:8000/api/v1/student/otp/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_number": "1A234567",
    "name": "Test User"
  }'

# 期待される応答:
# {
#   "email_aoyama": "1a234567@aoyama.ac.jp",
#   "message": "OTP sent successfully",
#   "expires_in_seconds": 600
# }

# DB に otp_records が追加されたか確認
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT email_aoyama, code, verified, verified_at 
FROM otp_records 
ORDER BY created_at DESC LIMIT 1;
EOF
```

### 4-2. OTP 検証テスト

```bash
# DB から最新の OTP コード取得
OTP_CODE=$(psql -h localhost -U postgres -d authwebapp -t -c "
SELECT code FROM otp_records ORDER BY created_at DESC LIMIT 1;
" | tr -d ' ')

echo "OTP コード: $OTP_CODE"

# OTP 検証
curl -X POST http://localhost:8000/api/v1/student/otp/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"code\": \"$OTP_CODE\"}"

# 期待される応答:
# {
#   "verified": true,
#   "message": "OTP 認証完了"
# }
```

### 4-3. ロール更新確認

OTP 検証後、以下を確認:

```bash
# 1. otp_records で verified フラグが TRUE になったか
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT email_aoyama, verified, verified_at 
FROM otp_records 
ORDER BY created_at DESC LIMIT 1;
EOF

# 2. user_memberships に membership_type='member' が追加されたか
# （Discord ID は otp_records から取得した discord_id で確認）
psql -h localhost -U postgres -d authwebapp << 'EOF'
SELECT discord_id, membership_type, assigned_at 
FROM user_memberships 
WHERE membership_type = 'member'
ORDER BY assigned_at DESC LIMIT 5;
EOF

# 3. role_member_assignments で member ロールが追加されたか（Discord との同期）
# これは Discord API の呼び出しが成功した場合のみ
```

---

## ステップ 5: データ検証レポート

テスト完了後、以下を確認してレポートを作成:

```bash
# スクリプトで検証結果を取得
cat > verify_test_results.sql << 'EOF'
-- 検証1: テーブル構造
\echo "=== テーブル構造 ==="
SELECT table_name, count(*) as column_count
FROM information_schema.columns
WHERE table_name IN ('users', 'user_memberships', 'student_profiles', 'paid_invitations')
GROUP BY table_name;

-- 検証2: データ件数
\echo "=== データ件数 ==="
SELECT 'user_memberships' as table_name, COUNT(*) FROM user_memberships
UNION ALL
SELECT 'member_list', COUNT(*) FROM member_list
UNION ALL
SELECT 'admin_list', COUNT(*) FROM admin_list
UNION ALL
SELECT 'pre_member_list', COUNT(*) FROM pre_member_list;

-- 検証3: membership_type 別件数
\echo "=== membership_type 別件数 ==="
SELECT membership_type, COUNT(*) as count
FROM user_memberships
GROUP BY membership_type
ORDER BY membership_type;

-- 検証4: 重複チェック
\echo "=== 重複ユーザー（1ユーザーが2つ以上の membership_type を持つ） ==="
SELECT COUNT(*) as duplicate_count
FROM (
    SELECT discord_id, COUNT(DISTINCT membership_type) as type_count
    FROM user_memberships
    GROUP BY discord_id
    HAVING COUNT(DISTINCT membership_type) > 1
) x;

-- 検証5: app_role カラム削除確認
\echo "=== app_role カラム削除確認 ==="
SELECT COUNT(*) as app_role_column_count
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'app_role';
EOF

psql -h localhost -U postgres -d authwebapp -f verify_test_results.sql > test_results.txt
cat test_results.txt
```

---

## ステップ 6: テスト結果チェックリスト

```markdown
## テスト結果チェックリスト

### SQL マイグレーション
- [ ] DB 接続 OK
- [ ] バックアップ作成 OK
- [ ] user_memberships テーブル作成 OK
- [ ] データ移行 OK（member_list, admin_list, pre_member_list）
- [ ] データ検証 OK（重複なし）
- [ ] SQL VIEW 作成 OK
- [ ] スキーマ修正 OK（app_role 削除など）

### Python コード
- [ ] ユーティリティ関数インポート OK
- [ ] DB 接続確認 OK
- [ ] user_memberships テーブル構造確認 OK
- [ ] 関数動作テスト OK
- [ ] スキーマ互換性確認 OK

### API エンドポイント
- [ ] GET /api/v1/members 応答 OK
- [ ] GET /api/v1/roles 応答 OK
- [ ] POST /api/v1/sync 動作 OK

### OTP フロー
- [ ] OTP 送信 OK
- [ ] OTP 検証 OK
- [ ] user_memberships に membership_type='member' 追加 OK
- [ ] role_member_assignments 更新（member ロール追加）OK
- [ ] role_member_assignments 更新（pre_member ロール削除）OK

### 最終確認
- [ ] すべてのテスト OK
- [ ] エラーログなし
- [ ] パフォーマンス問題なし
```

---

## ステップ 7: ステージング環境テストへの移行

開発環境テストが ** 完全に OK** になったら:

```bash
# 1. テスト結果をまとめたレポート作成
cat > TESTING_REPORT_DEV.md << 'EOF'
# 開発環境テストレポート

**実施日時**: $(date)
**テスト実行者**: [名前]
**テスト環境**: 開発用 PostgreSQL

## テスト結果
- ✓ SQL マイグレーション: OK
- ✓ Python コード検証: OK
- ✓ API エンドポイント検証: OK
- ✓ OTP フロー検証: OK

## 問題事項
[問題があればここに記載]

## 結論
すべてのテストが正常に完了した。本番環境への展開を推奨。
EOF

# 2. ステージング環境でのテスト手順実施
# → HANDOVER_DB_MIGRATION.md の「ステップ2: ステージング環境テスト」参照

# 3. 最終的に本番環境テスト実施へ
```

---

## トラブルシューティング

| 問題 | 原因 | 解決策 |
|------|------|--------|
| DB 接続エラー | PostgreSQL 未起動 | `docker-compose up -d postgres` |
| user_memberships 作成失敗 | テーブルが既に存在 | `DROP TABLE user_memberships` で削除後やり直し |
| 孤立レコード検出 | guild_members に discord_id が不足 | guild_members に該当レコードを追加 |
| OTP テスト失敗 | Discord API トークン無効 | 環境変数 DISCORD_TOKEN を確認 |
| API 応答エラー | backend コード問題 | ログを確認し、修正実施 |

---

## 次のステップ

✅ 開発環境テスト完了 → **ステージング環境テスト** → 本番環境展開

詳細は [HANDOVER_DB_MIGRATION.md](HANDOVER_DB_MIGRATION.md) を参照
