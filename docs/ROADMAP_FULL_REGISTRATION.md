# ロードマップ：本入会フォーム機能実装

**対象学生**: 青山学院大学の学生  
**実装期間**: 段階的（Phase 1 → Phase 3）  
**最終形**: サインイン後に自動ガード→フォーム表示→OTP認証→完了

---

## Phase 1: DB設計・マイグレーション

### 1.1 スキーマ拡張

#### (必須) student_profiles テーブル作成
```sql
CREATE TABLE student_profiles (
  id TEXT PRIMARY KEY,
  discord_id TEXT UNIQUE NOT NULL,
  student_number TEXT NOT NULL,
  name TEXT NOT NULL,
  furigana TEXT NOT NULL,
  department TEXT NOT NULL,
  gender TEXT,
  phone TEXT NOT NULL,
  email_aoyama TEXT NOT NULL DEFAULT '',
  email_verified BOOLEAN DEFAULT FALSE,
  email_verified_at TIMESTAMPTZ,
  otp_verified BOOLEAN DEFAULT FALSE,
  otp_verified_at TIMESTAMPTZ,
  profile_submitted_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

#### (必須) otp_records テーブル作成
```sql
CREATE TABLE otp_records (
  id TEXT PRIMARY KEY,
  discord_id TEXT NOT NULL,
  email_aoyama TEXT NOT NULL,
  code TEXT NOT NULL,
  attempt_count INTEGER DEFAULT 0,
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_otp_records_discord_id ON otp_records(discord_id);
CREATE INDEX idx_otp_records_expires_at ON otp_records(expires_at);
```

#### (既存) pre_member_list・paid_invitations テーブル確認
- `pre_member_list`: Discord ID から pre_member 権限を持つユーザー判定
- `paid_invitations`: 支払済みユーザー判定用（import from CSV）

### 1.2 マイグレーション実行
```bash
cd backend
alembic revision --autogenerate -m "add_student_profiles_otp_records"
alembic upgrade head
```

---

## Phase 2: Backend API 実装

### 2.1 新規エンドポイント設計

#### POST /api/v1/student/validate-eligibility
**説明**: 入会資格確認。ログイン後、フロント側がチェック  
**認証**: Bearer (Keycloak token)  
**レスポンス**:
```json
{
  "is_discord_linked": true,
  "is_pre_member": true,
  "is_paid": true,
  "can_register": true,
  "reason": "すべての条件を満たしています"
}
```

#### POST /api/v1/student/otp/send
**説明**: 大学メール(@aoyama.ac.jp)に OTP を送信  
**認証**: Bearer (Keycloak token)  
**リクエスト**:
```json
{
  "student_number": "A2412345",
  "name": "山田太郎"
}
```
**レスポンス**:
```json
{
  "email_aoyama": "a2412345@aoyama.ac.jp",
  "message": "OTP を送信しました。メールを確認してください",
  "expires_in_seconds": 600
}
```

#### POST /api/v1/student/otp/verify
**説明**: OTP を検証  
**認証**: Bearer (Keycloak token)  
**リクエスト**:
```json
{
  "code": "123456"
}
```
**レスポンス**:
```json
{
  "verified": true,
  "message": "OTP 認証完了"
}
```

#### POST /api/v1/student/profile
**説明**: 入会情報を保存  
**認証**: Bearer (Keycloak token)  
**リクエスト**:
```json
{
  "student_number": "A2412345",
  "name": "山田太郎",
  "furigana": "やまだたろう",
  "department": "経営学部経営学科",
  "gender": "male",
  "phone": "09012345678"
}
```
**レスポンス**:
```json
{
  "profile_id": "prof_...",
  "message": "登録完了。本会員として登録されました"
}
```

#### GET /api/v1/student/profile
**説明**: Pre-member が既に登録している情報を取得  
**認証**: Bearer (Keycloak token)  
**レスポンス**:
```json
{
  "student_number": "A2412345",
  "name": "山田太郎",
  "furigana": "やまだたろう",
  "department": "経営学部経営学科",
  "gender": "male",
  "phone": "09012345678"
}
```

### 2.2 実装手順

#### Step 1: alembic マイグレーション作成
- `backend/alembic/versions/000X_add_student_profiles.py` を作成
- `student_profiles`、`otp_records` テーブルの CREATE

#### Step 2: Brevo Email 統合
- `backend/app/services/brevo_client.py` に OTP 送信メソッド追加
- **メール本文テンプレート**:
```
ご入会ありがとうございます。
以下の OTP コードを入力してください（有効期限：10分）
コード: {code}
```

#### Step 3: Backend API 実装
- `backend/app/api/v1/student.py` を新規作成
- 上記 4 エンドポイントを実装
- 入力検証（学生番号形式、電話番号形式など）
- Discord ID から student_number 形式自動検出（オプション）

#### Step 4: テスト
- `backend/test_student_registration.py` で各 API をテスト

---

## Phase 3: Frontend 実装

### 3.1 ディレクトリ構造
```
frontend/src/
  app/join/
    form/
      page.tsx              ← メインフォームページ
      form-step-1.tsx       ← 資格確認画面
      form-step-2.tsx       ← 個人情報入力
      form-step-3.tsx       ← OTP認証
      form-step-4.tsx       ← 完了画面
    actions/
      register-student.ts   ← Server Action: フォーム送信
      check-eligibility.ts  ← Server Action: 資格確認
      send-otp.ts          ← Server Action: OTP送信
      verify-otp.ts        ← Server Action: OTP検証
```

### 3.2 フロー図
```
/join/form
  ↓
[Step 1] 資格確認ガード（初回のみ）
  - Discord ログイン確認
  - Pre-member 確認
  - 支払済リスト確認
  → 不可: /non-member へリダイレクト
  → 可能: Step 2 へ進む
  ↓
[Step 2] 個人情報入力フォーム
  - 学生番号 (必須)
  - 名前 (必須)
  - ふりがな (必須)
  - 学部学科 (選択)
  - 性別 (選択)
  - 電話番号 (必須)
  - Pre-member 情報がある場合は自動入力
  ↓
[Step 3] OTP 認証
  - メール送信ボタン
  - OTP コード入力フォーム
  - Resend ボタン（60秒待機）
  ↓
[Step 4] 完了
  - 本会員登録完了メッセージ
  - /roles へのリンク
```

### 3.3 コンポーネント実装

#### FormStep1: 資格確認
```tsx
// 以下を確認
1. session.user.discord_id 存在確認
2. API: GET /api/v1/student/validate-eligibility
3. 結果に応じたメッセージ表示
```

#### FormStep2: 個人情報入力
```tsx
// 以下を入力可能にする
1. Text input: 学生番号
2. Text input: 名前
3. Text input: ふりがな
4. Select dropdown: 学部学科（choices固定）
5. Radio group: 性別
6. Text input: 電話番号
// Pre-member情報がある場合は GET /api/v1/student/profile で取得して自動入力
```

#### FormStep3: OTP 認証
```tsx
// OTPInput.tsx（既存）を再利用
1. メール表示（xxx@aoyama.ac.jp）
2.「コードを送信」ボタン（POST /api/v1/student/otp/send）
3. OTP コード入力（6桁、自動フォーカス）
4. 検証（POST /api/v1/student/otp/verify）
5. Resend ボタン（次のリクエスト可能まで60秒カウントダウン）
```

### 3.4 Server Actions 実装例

#### check-eligibility.ts
```typescript
// GET /api/v1/student/validate-eligibility を呼び出し
// 結果に応じて以下を返す
// - { ok: true, ...eligibility }
// - { ok: false, reason: "..." }
```

#### register-student.ts
```typescript
// 1. フォーム検証
// 2. POST /api/v1/student/profile を呼び出し
// 3. 成功時: ページ遷移（/roles）
// 4. 失敗時: エラーメッセージ表示
```

---

## Phase 4: テスト・本番化（後続）

### 4.1 ローカルテスト
```bash
# 1. Docker コンテナ起動
docker compose up -d

# 2. マイグレーション実行
docker compose exec backend alembic upgrade head

# 3. Pre-member・支払済リスト登録（手動import）
docker compose exec postgres psql -U app -d authwebapp -c "..."

# 4. Frontend で /join/form にアクセス
# Discord ログイン → 資格確認 → フォーム入力 → OTP認証 → 完了
```

### 4.2 エンドツーエンドテスト項目
- [ ] 資格なキューザーは /non-member へリダイレクト
- [ ] Pre-member 情報は自動入力される
- [ ] OTP は10分で失効
- [ ] OTP 3回失敗でロック（実装TBD）
- [ ] 成功後は本会員としてDBに登録

### 4.3 本番デプロイ
- [ ] DB マイグレーション（必ず backup 取得後）
- [ ] Backend の新エンドポイントをデプロイ
- [ ] Frontend をビルド・デプロイ
- [ ] 監視ログ確認（エラーレート）

---

## 環境設定（Backend）

### 環境変数（追加）
```
# Brevo Email
BREVO_API_KEY=<your-key>
BREVO_FROM_EMAIL=noreply@example.com

# OTP
OTP_LENGTH=6
OTP_EXPIRY_SECONDS=600
OTP_MAX_ATTEMPTS=3

# メール生成ロジック
AOYAMA_EMAIL_FORMAT={student_number}@aoyama.ac.jp
```

---

## 参考: 学部学科マスター

```json
[
  { "code": "managment", "name": "経営学部経営学科" },
  { "code": "law", "name": "法学部法律学科" },
  { "code": "literature", "name": "文学部日本文学科" },
  ...（全学科分）
]
```

---

## まとめ

| Phase | 主要タスク | 工数 |
|-------|-----------|------|
| 1 | DB マイグレーション | 1-2h |
| 2 | Backend API（5 エンドポイント） | 4-6h |
| 3 | Frontend フォーム（4 ステップ） | 6-8h |
| 4 | テスト・デプロイ | 2-3h |
| **合計** | | **13-19h** |

---

**次ステップ**: Phase 1 から順にタスクボードで追跡して実装を進めてください。
