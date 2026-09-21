# DB 設計（PostgreSQL / Supabase）

本ドキュメントは、**Digitart サークル認証システム** で使用されているデータベーススキーマ（テーブル、ビュー、インデックス、運用ルール）の公式仕様です。
スキーマ定義およびマイグレーションは `backend/app/db/schema.py` および Alembic（`backend/alembic/versions/`）で管理されています。

---

## 1. ロール・カテゴリ管理

### `role_categories`
Discord ロールをグループ化して画面上にアコーディオン表示するための論理カテゴリ。

```sql
CREATE TABLE role_categories (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  display_order INTEGER DEFAULT 0,
  is_collapsed BOOLEAN DEFAULT FALSE,
  permissions BIGINT DEFAULT 0,
  is_restricted BOOLEAN DEFAULT FALSE  -- 管理者のみ編集可能なカテゴリフラグ
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### `role_manifests`
アプリケーションが宣言型（Desired State）で管理する Discord ロール定義。

```sql
CREATE TABLE role_manifests (
  role_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  color TEXT DEFAULT '#000000',
  hoist BOOLEAN DEFAULT FALSE,
  mentionable BOOLEAN DEFAULT FALSE,
  permissions BIGINT DEFAULT 0,
  position INTEGER NOT NULL,
  category_id TEXT REFERENCES role_categories(id) ON DELETE SET NULL,
  is_managed_by_app BOOLEAN DEFAULT TRUE,
  is_our_bot BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### `role_member_assignments`
ユーザーと Discord ロールの紐付け。

```sql
CREATE TABLE role_member_assignments (
  role_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  PRIMARY KEY (role_id, user_id)
);
```

---

## 2. ユーザー・権限管理（RBAC）

### `users`
Supabase Auth のアカウント（UUID）と Discord アカウント（`discord_id`）を紐付ける基本テーブル。

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  user_id TEXT UNIQUE NOT NULL,      -- Supabase auth.users の UUID
  discord_id TEXT UNIQUE,            -- Discord Snowflake ID
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### `user_memberships`
ユーザーに付与されたメンバーシップ権限を管理するテーブル（1ユーザーが複数の種別を持つことも可能）。

```sql
CREATE TABLE user_memberships (
  discord_id TEXT NOT NULL,
  membership_type TEXT NOT NULL CHECK (membership_type IN ('member', 'admin', 'pre_member', 'obog', 'sub_user')),
  assigned_by TEXT,
  assigned_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (discord_id, membership_type)
);

CREATE INDEX idx_user_memberships_discord_id ON user_memberships (discord_id);
CREATE INDEX idx_user_memberships_membership_type ON user_memberships (membership_type);
```

### `v_users_with_app_role`（VIEW）
`users` と `user_memberships` を結合し、アプリケーション上で有効な `app_role` を動的に算出する PostgreSQL ビュー。

```sql
CREATE OR REPLACE VIEW v_users_with_app_role AS
SELECT 
  u.id,
  u.user_id,
  u.discord_id,
  CASE 
    WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type = 'admin') THEN 'admin'
    WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type IN ('member','sub_user')) THEN 'member'
    WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type = 'obog') THEN 'obog'
    WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type = 'pre_member') THEN 'pre_member'
    ELSE 'none'
  END AS app_role,
  u.created_at,
  u.updated_at
FROM users u;
```

### `paid_invitations`
管理者が入会費（部費）の支払いを照合・承認・管理するためのテーブル。

```sql
CREATE TABLE paid_invitations (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  discord_id TEXT UNIQUE NOT NULL,
  user_id TEXT,
  note TEXT,
  expires_at TIMESTAMPTZ,
  assigned_by TEXT DEFAULT 'unknown',
  assigned_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### `guild_members`
Discord サーバーに所属するメンバーのキャッシュ情報。

```sql
CREATE TABLE guild_members (
  user_id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  display_name TEXT,
  avatar TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. 入会申請・学生認証（OTP）・アンケート

### `student_profiles`
在学生および本入会メンバーの学生プロフィール情報。

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
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  email_verified_at TIMESTAMPTZ,
  otp_verified BOOLEAN NOT NULL DEFAULT FALSE,
  otp_verified_at TIMESTAMPTZ,
  profile_submitted_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_student_profiles_student_number ON student_profiles (student_number);
CREATE INDEX idx_student_profiles_created_at ON student_profiles (created_at);
```

### `join_requests`
入学見込み生や外部からの問い合わせ・仮入会リクエスト情報。

```sql
CREATE TABLE join_requests (
  id TEXT PRIMARY KEY,               -- UUID
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  form_type TEXT NOT NULL,           -- prospective-student, contact 等
  status TEXT NOT NULL DEFAULT 'pending', -- pending, verified, completed, failed
  metadata JSONB,                    -- フォーム固有の追加項目
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_join_requests_email ON join_requests (email);
CREATE INDEX idx_join_requests_status ON join_requests (status);
```

### `otp_codes`
`join_requests` に紐づくメール認証用のワンタイムパスワード（OTP）。

```sql
CREATE TABLE otp_codes (
  id TEXT PRIMARY KEY,               -- UUID
  join_request_id TEXT NOT NULL REFERENCES join_requests(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL,           -- ハッシュ化されたコード
  expires_at TIMESTAMPTZ NOT NULL,
  verified_at TIMESTAMPTZ,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_otp_codes_join_request_id ON otp_codes (join_request_id);
CREATE INDEX idx_otp_codes_expires_at ON otp_codes (expires_at);
```

### `otp_records`
在学生向け（大学メールアドレス宛）のワンタイムパスワード（OTP）認証記録。

```sql
CREATE TABLE otp_records (
  id TEXT PRIMARY KEY,
  discord_id TEXT NOT NULL,
  email_aoyama TEXT NOT NULL,
  code TEXT NOT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_otp_records_discord_id ON otp_records (discord_id);
CREATE INDEX idx_otp_records_expires_at ON otp_records (expires_at);
```

### `member_survey_responses`
本入会時に回答されたサークル活動や認知経路に関するアンケートデータ。

```sql
CREATE TABLE member_survey_responses (
  id BIGSERIAL PRIMARY KEY,
  student_number VARCHAR(32) NOT NULL,
  digitart_channels JSONB DEFAULT '[]'::jsonb,
  digitart_channels_other TEXT,
  circle_search_channels JSONB DEFAULT '[]'::jsonb,
  circle_search_other TEXT,
  discord_invite_source TEXT,
  interested_fields JSONB DEFAULT '[]'::jsonb,
  interested_fields_other TEXT,
  motivations JSONB DEFAULT '[]'::jsonb,
  motivations_other TEXT,
  raw_payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_member_survey_student_number ON member_survey_responses(student_number);
CREATE INDEX idx_member_survey_created_at ON member_survey_responses(created_at);
```

### `pre_member_removal_log`
仮入会（pre_member）ロールの有効期限切れ等に伴う自動解除・剥奪の監査ログ。

```sql
CREATE TABLE pre_member_removal_log (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  discord_id TEXT NOT NULL,
  source_flow TEXT,
  expired_at TIMESTAMPTZ,
  removed_at TIMESTAMPTZ DEFAULT now(),
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. 運用・セキュリティルール

1. **個人情報（PII）の保護**:
   - `student_profiles`（氏名、電話番号、学生番号）や `join_requests`（メールアドレス）は機密情報（PII）です。ログ出力やエラーレスポンスに生値を含めないこと。
2. **権限判定の原則**:
   - アプリケーション側の権限判定は `v_users_with_app_role` ビューを参照して行います（テーブル直接操作による不整合を防ぐため）。
3. **ロール優先度（Position）**:
   - `role_manifests.position` は Discord のロール階層順序と連動します。Bot による差分同期時に利用されます。
4. **マイグレーション運用**:
   - スキーマ変更時は Alembic マイグレーションスクリプトを作成し、ローカル検証後に CI で整合性を確認してください。

