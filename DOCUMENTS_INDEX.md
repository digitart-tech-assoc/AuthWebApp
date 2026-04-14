# DB スキーマ移行プロジェクト - ドキュメント一覧

**プロジェクト**: user_memberships テーブル統合  
**ステータス**: コード実装完了 → 開発環境テスト準備完了  
**最終更新**: 2026年4月14日

---

## 📚 ドキュメント構成

### 1️⃣ **概要・計画ドキュメント**

#### [DB_SCHEMA_ANALYSIS_AND_PROPOSAL.md](DB_SCHEMA_ANALYSIS_AND_PROPOSAL.md)
**内容**: DB スキーマ分析と改善提案
- 現在の DB スキーマ 25 テーブル分析
- 冗長性の特定（member_list, admin_list, pre_member_list）
- 提案: 12 テーブル統合スキーマ
- user_memberships テーブル設計
- マイグレーション影響範囲分析
- **対象読者**: アーキテクト、技術リード
- **用途**: スキーマ変更の背景理解

#### [MIGRATION_PLAN_DATA_TRANSFER.md](MIGRATION_PLAN_DATA_TRANSFER.md)
**内容**: SQL マイグレーション手順書（7フェーズ）
- フェーズ1: 準備（バックアップ、テーブル作成）
- フェーズ2: データ移行（INSERT）
- フェーズ3-5: スキーマ修正（カラム削除）
- フェーズ6-7: クリーンアップ
- ロールバック手順
- **対象読者**: DBA、DevOps
- **用途**: 本番環境への SQL 実行手順

#### [IMPLEMENTATION_GUIDE_AFTER_MIGRATION.md](IMPLEMENTATION_GUIDE_AFTER_MIGRATION.md)
**内容**: コード修正実装ガイド（7フェーズ A-G）
- Phase A: user_repository.py（app_role 計算）
- Phase B-C: repository.py（sync/get 関数）
- Phase D: reconcile.py（pre_member 読込元）
- Phase E: members.py（add_to_member_list）
- Phase F: auth.py, student.py, roles.py（検証）
- Phase G: ユーティリティ関数統合
- **対象読者**: 開発チーム
- **用途**: Python コード修正の詳細手順

#### ✅ **実装済み** ← コード修正はすべて完了

---

### 2️⃣ **実行・テストドキュメント**

#### [HANDOVER_DB_MIGRATION.md](HANDOVER_DB_MIGRATION.md) 📋 **メイン引き継ぎ書類**
**内容**: 完全な引き継ぎ書類（包括的）
- スキーマ変更内容（Before/After）
- コード実装完了リスト（Phase A-G）
- 開発環境テスト手順
- SQL マイグレーション手順（詳細版）
- ロールバック手順
- 本番環境展開スケジュール
- テスト結果チェックリスト
- **対象読者**: テスト実施者、プロジェクトマネージャー
- **用途**: 開発環境から本番環境への一貫したガイド

#### [DEV_TEST_EXECUTION_GUIDE.md](DEV_TEST_EXECUTION_GUIDE.md) 🧪 **開発環境テスト実行ガイド**
**内容**: 開発環境でのステップごとのテスト実行方法
- ステップ 1: SQL マイグレーション（自動テスト）
- ステップ 2: Python コード検証
- ステップ 3: Backend API 検証
- ステップ 4: OTP フロー検証
- ステップ 5: データ検証レポート
- ステップ 6: チェックリスト
- ステップ 7: ステージング環境への移行
- トラブルシューティング表
- **対象読者**: 開発チーム（テスト実施者）
- **用途**: 実際のテスト実行

---

### 3️⃣ **自動化テストスクリプト**

#### [test_db_migration_dev.sh](test_db_migration_dev.sh) 🔧 **SQL 自動テストスクリプト**
**内容**: DB 移行を自動で実行・検証
```bash
./test_db_migration_dev.sh         # 通常実行
./test_db_migration_dev.sh --rollback  # ロールバック
```
**検証項目**:
- DB 接続確認
- バックアップ作成
- user_memberships テーブル作成
- guild_members 整合性確認
- データ移行（member_list, admin_list, pre_member_list）
- データ検証（重複チェック）
- SQL VIEW 作成
- スキーマ修正
- **実行時間**: 約 2-3分
- **前提条件**: PostgreSQL 稼働中

#### [test_python_code_migration_dev.py](test_python_code_migration_dev.py) 🐍 **Python コード検証スクリプト**
**内容**: Python backend コード互換性検証
```bash
python test_python_code_migration_dev.py
```
**検証項目**:
- ユーティリティ関数インポート
- user_repository 関数確認
- DB 接続確認
- user_memberships テーブル構造確認
- app_role カラム削除確認
- 関数の動作テスト
- スキーマ互換性確認
- **実行時間**: 約 1-2分
- **前提条件**: backend/ に移動、requirements.txt インストール済み

---

### 4️⃣ **参考資料**

#### 既存ドキュメント
- `docs/api.md` - API ドキュメント
- `docs/backend.md` - Backend アーキテクチャ
- `docs/db.md` - DB スキーマドキュメント
- `docs/discord-bot.md` - Discord Bot ドキュメント

#### コード実装ファイル（修正済み）
1. ✅ `backend/alembic/migration_view_users_with_app_role.sql` - SQL VIEW
2. ✅ `backend/app/db/user_repository.py` - Phase A
3. ✅ `backend/app/db/repository.py` - Phases B, C, G
4. ✅ `backend/app/api/v1/members.py` - Phase E
5. ✅ `discord-bot/app/services/reconcile.py` - Phase D
6. ✅ `backend/app/core/auth.py` - 検証済み（変更不要）
7. ✅ `backend/app/api/v1/student.py` - 検証済み（変更不要）
8. ✅ `backend/app/api/v1/roles.py` - 検証済み（変更不要）

---

## 🎯  実行フロー

### 開発環境テスト（今ここ）

```
┌─────────────────────────────┐
│ 1. SQL マイグレーション      │
│ (test_db_migration_dev.sh)  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 2. Python コード検証         │
│ (test_python_code_...)      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 3. Backend API テスト        │
│ (curl -X GET /api/v1/...)   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 4. OTP フロー検証            │
│ (send + verify)             │
└──────────────┬──────────────┘
               │
               ▼
         ✅ 完了
         
         ↓ (すべて OK の場合)
         
     ステージング環境テスト
```

### テスト実行チェックリスト

```markdown
## 開発環境テスト（1-2日）
- [ ] SQL 自動テスト実行
  - [ ] DB 接続確認
  - [ ] バックアップ作成
  - [ ] データ移行
  - [ ] データ検証
  - [ ] ロールバック動作確認
  
- [ ] Python コード検証
  - [ ] ユーティリティ関数確認
  - [ ] 関数動作テスト
  
- [ ] API エンドポイント検証
  - [ ] GET /api/v1/members
  - [ ] GET /api/v1/roles
  - [ ] POST /api/v1/sync
  
- [ ] OTP フロー検証
  - [ ] OTP 送信
  - [ ] OTP 検証
  - [ ] role_member_assignments 更新確認

## ステージング環境テスト（1日）
- [ ] 本番同等環境でテスト実行
- [ ] 想定ダウンタイム検証（5-10分）
- [ ] ロールバック手順テスト

## 本番環境展開（準備）
- [ ] 非ピーク時（深夜 0:00-2:00）スケジューリング
- [ ] サポート体制確認
- [ ] ロールバック待機
```

---

## 🚀 クイックスタート

### 1️⃣ **開発環境テスト実行（5分で開始）**

```bash
cd /home/chrom/develops/AuthWebApp

# テストスクリプト実行権限付与
chmod +x test_db_migration_dev.sh

# SQL マイグレーションテスト 実行
./test_db_migration_dev.sh

# Python コード検証
python test_python_code_migration_dev.py

# 詳細な手順は DEV_TEST_EXECUTION_GUIDE.md を参照
```

### 2️⃣ **テスト結果確認**

すべてのテストが ✅ OK なら、HANDOVER_DB_MIGRATION.md の「ステップ2: ステージング環境テスト」に進む。

### 3️⃣ **本番環境展開準備**

ステージング環境テスト完了後、HANDOVER_DB_MIGRATION.md の「ステップ3: 本番環境展開」を実行。

---

## 📞 サポート情報

### 問題が発生した場合

1. **エラーログ確認**
   ```bash
   docker-compose logs postgres    # DB ログ
   cat backend.log                 # Backend ログ
   cat test_results.txt            # テスト結果
   ```

2. **該当ドキュメントを確認**
   - SQL 関連: MIGRATION_PLAN_DATA_TRANSFER.md
   - Python コード: IMPLEMENTATION_GUIDE_AFTER_MIGRATION.md
   - テスト手順: DEV_TEST_EXECUTION_GUIDE.md
   - トラブルシューティング: DEV_TEST_EXECUTION_GUIDE.md#トラブルシューティング

3. **ロールバック実行**
   ```bash
   ./test_db_migration_dev.sh --rollback
   ```

### 連絡先
- 開発チーム Slack: [#development]
- DBA: [DBA contact]
- 緊急: [Emergency contact]

---

## 📈 プロジェクト進捗

```
[████████████████████░░░░░░░░░░░░] 70% Complete

Done:
 ✅ DB スキーマ分析
 ✅ Python コード実装（Phase A-G）
 ✅ ドキュメント作成
 ✅ 自動テストスクリプト

In Progress:
 🔄 開発環境テスト

To Do:
 ⏳ ステージング環境テスト
 ⏳ 本番環境展開
 ⏳ 本番環境検証
```

---

## 📋 最終チェックリスト（本番前）

- [ ] 開発環境テスト：全項目 OK
- [ ] ステージング環境テスト：全項目 OK
- [ ] ロールバック手順：検証済み
- [ ] 本番環境スケジュール：確認済み
- [ ] サポート体制：整備完了
- [ ] 緊急連絡先：周知完了

---

**次のステップ**: [DEV_TEST_EXECUTION_GUIDE.md](DEV_TEST_EXECUTION_GUIDE.md) でテスト実行を開始
