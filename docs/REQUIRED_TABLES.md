# 必要テーブル確認リスト

**更新日**: 2026-03-27  
**対象**: 本入会フォーム機能実装

---

## 現在の実装状況

### ✅ 既に作成済みのテーブル

#### Phase 1 マイグレーション (0003_add_student_registration.py)

| テーブル名 | 主な列 | 用途 |
|-----------|--------|------|
| **student_profiles** | id, discord_id, student_number, name, furigana, department, gender, phone, email_aoyama, email_verified, otp_verified, profile_submitted_at | 学生の本入会情報保存 |
| **otp_records** | id, discord_id, email_aoyama, code, attempt_count, verified, expires_at | OTP認証記録（一時テーブル） |

#### 既存テーブル（プリセット）

| テーブル名 | 用途 | 状態 |
|-----------|------|------|
| pre_member_list | Pre-member 権限判定（Discord ID リスト） | ✅ 既存・利用可 |
| paid_invitations | 支払済みユーザー判定（Discord ID リスト） | ✅ 既存・利用可 |

---

## ❌ 追加で必要なテーブル

### users テーブル（未作成）

**要件**: Supabase user ID と Discord ID のマッピング

**必須理由**:
- Supabase Auth ユーザー（sub=UUID）と Discord ID を紐付ける
- Backend が Supabase JWT から取得した user ID を使用して、ユーザー情報を検索する
- app_role（admin/member/pre_member/none）を保存する

**スキーマ案**:
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,                              -- Supabase user ID (UUID)
  discord_id TEXT UNIQUE,                           -- Discord ID
  email TEXT,                                       -- Supabase email
  app_role TEXT DEFAULT 'none',                     -- admin/member/pre_member/none
  is_alumni BOOLEAN DEFAULT FALSE,
  withdrawn_at TIMESTAMPTZ,
  data_retention_until TIMESTAMPTZ,
  deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_discord_id ON users(discord_id);
```

**マイグレーション**: `0004_add_users_table.py`（別途作成予定）

---

## テーブル関連図

```
Supabase Auth
    ↓
    └─→ user_metadata { discord_id: "..." }
         ↓
         users テーブル (Supabase user ID ← → Discord ID)
         ↓
         ├─→ student_profiles (discord_id で JOIN)
         │    └─ 学生個人情報
         │
         ├─→ otp_records (discord_id で JOIN)
         │    └─ OTP認証履歴
         │
         └─→ pre_member_list / paid_invitations (Discord ID で参照)
              └─ 権限判定
```

---

## 実装チェックリスト

### テーブル
- [x] student_profiles テーブル作成
- [x] otp_records テーブル作成
- [ ] **users テーブル作成** (新規作成予定)

### Backend
- [x] 5つの API エンドポイント実装
- [x] Brevo Email 送信機能
- [ ] **Supabase JWT 検証ロジック** (修正予定)

### Frontend
- [x] 4ステップフォーム UI
- [x] Server Actions 実装
- [ ] **Supabase session 対応** (修正予定)

---

## 次のステップ

1. **マイグレーション作成**: `backend/alembic/versions/0004_add_users_table.py`
   ```bash
   cd backend
   alembic revision --autogenerate -m "add_users_table"
   alembic upgrade head
   ```

2. **Backend JWT 検証更新**: `backend/app/core/auth.py`
   - Keycloak → Supabase JWT 検証に切り替え
   - Discord ID 抽出ロジック（user_metadata から）

3. **Frontend Supabase 対応**: 
   - `frontend/src/actions/student-registration.ts` を修正
   - `getBackendAuthorizationHeader()` が Supabase session を使用

4. **テスト実行**
   - ローカル環境で全テストケース実行
   - Supabase 本番プロジェクトへのデプロイ

---

## 詳細は別ドキュメント参照

- [SUPABASE_AUTH_MIGRATION.md](SUPABASE_AUTH_MIGRATION.md) - Supabase への移行ガイド
- [ROADMAP_FULL_REGISTRATION.md](ROADMAP_FULL_REGISTRATION.md) - 全体ロードマップ
- [TEST_GUIDE_FULL_REGISTRATION.md](TEST_GUIDE_FULL_REGISTRATION.md) - テストガイド
