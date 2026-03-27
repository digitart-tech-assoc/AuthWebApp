# 本入会フォーム機能 実装完了レポート

**実装日**: 2026-03-27  
**ステータス**: フェーズ1・2 完了、テスト準備中

---

## 📝 実装したファイル一覧

### Backend

#### 1. **Alembic マイグレーション**
- `backend/alembic/versions/0003_add_student_registration.py`
  - `student_profiles` テーブル
  - `otp_records` テーブル
  - インデックス設定

#### 2. **API エンドポイント**
- `backend/app/api/v1/student.py` （新規）
  - `POST /api/v1/student/validate-eligibility` - 入会資格確認
  - `POST /api/v1/student/profile` - プロフィール保存（新規・更新）
  - `GET /api/v1/student/profile` - プロフィール取得
  - `POST /api/v1/student/otp/send` - OTP コード送信
  - `POST /api/v1/student/otp/verify` - OTP 検証

#### 3. **Brevo Email 統合**
- `backend/app/services/brevo_client.py` （修正）
  - `send_otp_email()` 同期ラッパー関数追加

#### 4. **ルータ登録**
- `backend/app/main.py` （修正）
  - `student_router` インク ル ード

### Frontend

#### 1. **Server Actions**
- `frontend/src/actions/student-registration.ts` （新規）
  - `checkEligibility()`
  - `getStudentProfile()`
  - `sendOTP()`
  - `verifyOTP()`
  - `submitStudentProfile()`

#### 2. **ページコンポーネント**
- `frontend/src/app/join/form/page.tsx` （修正）
  - メインフォームページ（4ステップフロー管理）

#### 3. **ステップコンポーネント**
- `frontend/src/app/join/form-step-1.tsx` （新規）
  - 入会資格確認画面
  - Discord・Pre-member・支払済み確認表示
  
- `frontend/src/app/join/form-step-2.tsx` （新規）
  - 個人情報入力フォーム（学生番号、名前、ふりがな、学部学科、性別、電話番号）
  - Pre-member 情報がある場合は自動入力
  - フォーム検証機能
  
- `frontend/src/app/join/form-step-3.tsx` （新規）
  - OTP 送信・認証画面
  - 60秒 resend クールダウン
  - OTP Input コンポーネント統合
  
- `frontend/src/app/join/form-step-4.tsx` （新規）
  - 登録完了画面
  - メンバーページへのリンク

---

## 🔄 入会フロー フロー図

```
サイトアクセス (/join/form)
    ↓
[ページ読み込み] Supabase Auth session 確認
    ↓
[Step 1] validate-eligibility API 呼び出し
    - Discord ログイン確認（Supabase user_metadata から Discord ID 抽出）
    - pre_member_list チェック
    - paid_invitations チェック
    ↓ (全条件 OK の場合)
[Step 2] 個人情報入力
    - 既存プロフィール自動入力（あれば）
    - フォーム検証・送信可
    ↓
[Step 3] OTP 認証
    - POST /api/v1/student/otp/send
    - メール受信
    - コード入力 → POST /api/v1/student/otp/verify
    - 検証完了 → POST /api/v1/student/profile
    ↓
[Step 4] 完了
    - 登録確認メッセージ
    - /roles ページへナビゲ ー ト
```

---

## 🛠 DB スキーマ

### `student_profiles`
```sql
CREATE TABLE student_profiles (
  id TEXT PRIMARY KEY,                              -- UUID
  discord_id TEXT UNIQUE NOT NULL,                  -- Discord ID
  student_number TEXT NOT NULL,                     -- 学生番号（A2312345 形式）
  name TEXT NOT NULL,                               -- 名前
  furigana TEXT NOT NULL,                           -- ふりがな
  department TEXT NOT NULL,                         -- 学部学科
  gender TEXT,                                      -- 性別（male/female/other）
  phone TEXT NOT NULL,                              -- 電話番号
  email_aoyama TEXT DEFAULT '',                     -- 大学メール（自動生成）
  email_verified BOOLEAN DEFAULT FALSE,             -- メール認証済みフラグ
  email_verified_at TIMESTAMPTZ,                    -- メール認証日時
  otp_verified BOOLEAN DEFAULT FALSE,               -- OTP 検証済みフラグ
  otp_verified_at TIMESTAMPTZ,                      -- OTP 検証日時
  profile_submitted_at TIMESTAMPTZ,                 -- プロフィール送信日時
  updated_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_student_profiles_student_number ON student_profiles(student_number);
CREATE INDEX idx_student_profiles_created_at ON student_profiles(created_at);
```

### `otp_records`
```sql
CREATE TABLE otp_records (
  id TEXT PRIMARY KEY,                              -- UUID
  discord_id TEXT NOT NULL,                         -- Discord ID
  email_aoyama TEXT NOT NULL,                       -- 送信先メール
  code TEXT NOT NULL,                               -- OTP コード（6桁）
  attempt_count INTEGER DEFAULT 0,                  -- 試行回数
  verified BOOLEAN DEFAULT FALSE,                   -- 検証済みフラグ
  verified_at TIMESTAMPTZ,                          -- 検証日時
  expires_at TIMESTAMPTZ NOT NULL,                  -- 有効期限
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_otp_records_discord_id ON otp_records(discord_id);
CREATE INDEX idx_otp_records_expires_at ON otp_records(expires_at);
```

---

## 🚀 次ステップ：テストと本番化

### 1. ローカルテスト（環境構築）
```bash
# 1. Alembic マイグレーション実行
cd backend
alembic upgrade head

# 2. Docker 再ビルド
cd ../
docker compose down
docker compose up --build -d

# 3. Pre-member/支払済みリスト登録（テスト用）
docker compose exec postgres psql -U app -d authwebapp -c "
INSERT INTO pre_member_list (discord_id) VALUES ('test_discord_id_123');
INSERT INTO paid_invitations (discord_id) VALUES ('test_discord_id_123');
"

# 4. フロント側で /join/form にアクセス
# http://localhost:3000/join/form
```

### 2. 環境変数設定（.env.local など）
```bash
# Backend
BREVO_API_KEY=<your-brevo-api-key>
BREVO_SENDER_EMAIL=noreply@digitart.example.com
BREVO_SENDER_NAME=Digitart Technology Society
OTP_LENGTH=6
OTP_EXPIRY_SECONDS=600
OTP_MAX_ATTEMPTS=3
AOYAMA_EMAIL_FORMAT={student_number}@aoyama.ac.jp
```

### 3. テスト項目
- [ ] Discord がリンクされていないユーザー → /non-member へリダイレクト
- [ ] Pre-member 登録なし → 資格確認エラー表示
- [ ] 支払済み登録なし → 資格確認エラー表示
- [ ] 全条件満たす → Step 2 へ進行
- [ ] Pre-member 情報あり → Step 2 で自動入力
- [ ] 学生番号の形式チェック
- [ ] 電話番号の形式チェック
- [ ] OTP コード 3 回失敗 → ロック
- [ ] OTP 有効期限（600秒）後 → 再送信
- [ ] 成功時 → /roles へナビゲ ー ト

### 4. 本番デプロイチェックリスト
- [ ] DB バックアップ取得
- [ ] `alembic upgrade head` 実行
- [ ] Backend コンテナ再ビルド・デプロイ
- [ ] Frontend ビルド・デプロイ
- [ ] Brevo API key 設定確認
- [ ] メール送信テスト
- [ ] 監視ログ確認（エラーレート・OTP 送信成功率）
- [ ] ユーザーテスト（内部）

---

## 📝 今後の拡張予定

### Phase 4 以降の可能性
1. **OBOG（卒業生）向け入会フォーム**
   - `/join/form/obog` ページ
   - 個人情報フォーム定義調整

2. **一般向け入会問い合わせ**
   - その他カテゴリのユーザー向け情報提供

3. **入会の承認ワークフロー**
   - 管理者による承認機能
   - 通知システム統合

4. **データ保持ポリシー適用**
   - `users.data_retention_until` を用いた GDPR 対応
   - 過期データの自動削除

---

## 🔗 相関図

```
User Access
   ↓
/join/form (page.tsx)
   ├── validate-eligibility (Server Action)
   │   └── GET /api/v1/student/validate-eligibility (Backend)
   │
   ├── FormStep2Input
   │   └── getStudentProfile (Server Action)
   │       └── GET /api/v1/student/profile (Backend)
   │
   ├── FormStep3OTP
   │   ├── sendOTP (Server Action)
   │   │   └── POST /api/v1/student/otp/send (Backend)
   │   │       └── send_otp_email (Brevo)
   │   │
   │   └── verifyOTP + submitStudentProfile
   │       ├── POST /api/v1/student/otp/verify (Backend)
   │       └── POST /api/v1/student/profile (Backend)
   │           └── INSERT/UPDATE student_profiles
   │
   └── FormStep4Complete → /roles (redirect)
```

---

## 📊 API レスポンス例

### GET `/api/v1/student/validate-eligibility` (成功)
```json
{
  "is_discord_linked": true,
  "is_pre_member": true,
  "is_paid": true,
  "can_register": true,
  "reason": "すべての条件を満たしています"
}
```

### POST `/api/v1/student/otp/send` (成功)
```json
{
  "email_aoyama": "a2312345@aoyama.ac.jp",
  "message": "OTP を送信しました。メールを確認してください",
  "expires_in_seconds": 600
}
```

### POST `/api/v1/student/profile` (成功)
```json
{
  "profile_id": "prof_abc123def456",
  "student_number": "A2312345",
  "name": "山田太郎",
  "email_aoyama": "a2312345@aoyama.ac.jp",
  "message": "登録完了。本会員として登録されました"
}
```

---

## ✅ チェックリスト

- [x] Alembic マイグレーション作成
- [x] Backend API エンドポイント実装（5個）
- [x] Brevo Email 統合
- [x] Frontend フォームコンポーネント（4ステップ）
- [x] Server Actions 実装
- [x] Form validation ロジック
- [ ] ローカルテスト実行
- [ ] CI/CD パイプル構成（別途）
- [ ] 本番デプロイ

---

**次のステップ**: テスト環境で動作確認 → 本番化
