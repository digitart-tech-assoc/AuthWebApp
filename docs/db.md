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

### `role_audit_logs`
ロール定義・割り当ての変更履歴（監査ログ）。DB への変更と、Backend が Discord に加えた変更の両方を記録します（Alembic `0007_add_role_audit_logs`）。
保存するのは ID（Supabase UUID / Discord ID）とロール定義だけで、メンバーの名前などの個人情報は保存しません。閲覧用の API・画面はないため、Supabase の SQL エディタで確認します。

```sql
CREATE TABLE role_audit_logs (
  id               TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  occurred_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  request_id       TEXT NOT NULL,   -- 1回の API 呼び出しで書いた行をまとめる ID（アプリのログの request_id と同じ）
  operation        TEXT NOT NULL,   -- 下の表を参照
  system           TEXT NOT NULL CHECK (system IN ('db', 'discord')),
  target_type      TEXT NOT NULL,   -- 下の表を参照
  target_id        TEXT NOT NULL,
  action           TEXT NOT NULL,   -- 下の表を参照
  before           JSONB,           -- 変更のあったフィールドだけ
  after            JSONB,
  actor_sub        TEXT,            -- Supabase UUID または 'internal-service'
  actor_discord_id TEXT             -- 操作した人の Discord ID（内部連携からの呼び出しでは NULL）
);
CREATE INDEX idx_role_audit_logs_target ON role_audit_logs (target_type, target_id, occurred_at DESC);
CREATE INDEX idx_role_audit_logs_occurred_at ON role_audit_logs (occurred_at DESC);
```

#### 値の定義

| カラム | 値 | 意味 |
|---|---|---|
| `operation` | `manifest_patch` | `PATCH /api/v1/manifest` |
| | `manifest_put` | `PUT /api/v1/manifest` |
| | `push` | `POST /api/v1/roles/push` |
| | `self_batch` | `POST /api/v1/roles/self-batch` |
| | `self_create` | `POST /api/v1/roles/self-create` |
| | `join_otp_verify` | `POST /api/v1/student/otp/verify` |
| | `student_profile` | `POST /api/v1/student/profile` |
| | `pre_member_register` | `POST /api/v1/members/pre_member/register`（Bot からの内部呼び出し） |
| `system` | `db` | DB への変更 |
| | `discord` | Discord への変更 |
| `target_type` | `category` | `target_id` = カテゴリ ID |
| | `role` | `target_id` = ロール ID（ロール定義の変更） |
| | `role_assignment` | `target_id` = ロール ID（ロール単位で見た割り当ての変更。マニフェスト保存で使う） |
| | `member_roles` | `target_id` = Discord ユーザー ID（メンバー単位で見たロールの付け外し。push・self-batch・入会・pre-member 登録で使う） |
| `action` | `create` / `update` / `delete` | 作成・更新・削除 |
| | `rename_id` | 仮 ID（`draft-…`）を正式な ID に置き換え |
| | `reorder` | 並び順の変更 |
| | `rollback` | self-batch・self-create の DB 更新に失敗したため、Discord の変更を元に戻した（self-create では、作成したロールの削除と作成者への付与の取り消し） |

#### `before` / `after` の形式
- 値の形式は `fetch_manifest` / `fetch_guild_roles` の戻り値に合わせます（`permissions` は int、`color` は文字列）。Discord API に送る形式（`permissions` は str、`color` は int）ではありません。
- **DB 側の行:** 変更前と変更後の行を比べ、変わったフィールドだけを記録します。作成は `before` が NULL で `after` に全フィールド、削除は `before` に全フィールドで `after` が NULL です。
  - カテゴリの比較対象: `name`, `display_order`, `is_collapsed`, `permissions`, `is_restricted`
  - ロールの比較対象: `name`, `color`, `hoist`, `mentionable`, `permissions`, `position`, `category_id`, `is_our_bot`
  - カテゴリを削除すると、属していたロールの `category_id` が `ON DELETE SET NULL` で NULL になります。これもロールの `update` として記録します。
- **Discord 側のロール更新の行:** Discord に実際に送ったフィールドだけを、`before` に Discord 側の変更前の値、`after` に DB の値で記録します。
- **Discord 側のロール作成・削除の行:** 作成は `after` に Discord の応答（`name`, `color`, `hoist`, `mentionable`, `permissions`, `position`）、削除は `before` に削除前の定義を記録します。
- **並び替え（`reorder`）の行:** ほかのロールとの相対的な順序が変わったロールだけを、1ロール1行で `{"position": <Discord 上の値>}` → `{"position": <送信した値>}` として記録します。ロールの作成・削除で `position` が一律にずれただけのロールは記録しません。
  - 対象は「順序を保ったまま残せる最大のロールの集まり（最長増加部分列）に含まれないロール」です。最長増加部分列が複数ある場合はそのうち1つを使うため、**どのロールが記録されるかは一意ではありません**（件数は push のレスポンスの `reordered` と一致します）。
- **割り当て（`role_assignment` / `member_roles`）:** 実際に追加・削除されたものだけを `after = {"added": [...], "removed": [...]}` で記録します（`before` は NULL）。

#### `color` の表記
`color` は正規化していないため、大文字・小文字の表記が混ざります。
- DB 側の行は、保存された文字列のまま記録します（画面の色の候補が大文字のため、`#99AAB5` のような大文字を含むことがあります）。`#99AAB5` → `#99aab5` のような表記だけの変更も、DB の変更として記録されます。
- Discord 側の行は、`fetch_guild_roles` が返す小文字の `#rrggbb` で記録します。Discord への送信は色を数値にして比べるため、大文字・小文字だけが違う色は Discord 側の行に記録されません。

#### 記録のタイミングと失敗時の動作
- **DB への変更（`system = 'db'`）:** 変更と同じトランザクションで記録します。記録に失敗したら、その変更も失敗します。
  - 例外: `POST /api/v1/student/otp/verify` は、割り当ての更新（と記録）に失敗しても OTP 検証は成功として返します（従来どおり）。
  - `rename_id` の記録に失敗すると、DB のロールは `draft-…` のまま残ります。次の push でロールが作り直され、前回作ったロール（DB にないロール）は削除されます。前回作ったロールの ID は、Discord 側の `create` の行から追えます。
- **Discord への変更（`system = 'discord'`）:** Discord API の呼び出しが成功するたびに、その場で記録します。記録に失敗しても元の処理は続け、Backend のログにエラーを出します。

#### 確認用の SQL

```sql
-- 直近の変更
SELECT occurred_at, operation, system, target_type, target_id, action, before, after, actor_sub
FROM role_audit_logs
ORDER BY occurred_at DESC
LIMIT 100;

-- 1回の push で書いた行（request_id は Backend のログの「role audit: request_id=...」から分かる）
SELECT occurred_at, system, target_type, target_id, action, before, after
FROM role_audit_logs
WHERE request_id = '<request_id>'
ORDER BY occurred_at;

-- 特定のロールの履歴（仮 ID のうちに保存した変更も含める）
-- 仮 ID のうちの変更は target_id = 'draft-…' で記録されるため、rename_id の行から仮 ID をたどる
WITH ids AS (
  SELECT '<role_id>' AS id
  UNION
  SELECT before->>'role_id'
  FROM role_audit_logs
  WHERE target_type = 'role' AND action = 'rename_id' AND target_id = '<role_id>'
)
SELECT occurred_at, operation, system, target_type, target_id, action, before, after, actor_sub
FROM role_audit_logs
WHERE target_type IN ('role', 'role_assignment') AND target_id IN (SELECT id FROM ids)
ORDER BY occurred_at;

-- push で Discord 側の権限を上書きした記録（Discord で直接変更された値が before に残る）
SELECT occurred_at, target_id, before->'permissions' AS discord_before, after->'permissions' AS db_value
FROM role_audit_logs
WHERE system = 'discord' AND operation = 'push' AND action = 'update' AND after ? 'permissions'
ORDER BY occurred_at DESC;
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
ビューは既定では所有者の権限で動き元テーブルの RLS を素通りするため、`security_invoker = on` を必ず指定する。

```sql
CREATE OR REPLACE VIEW v_users_with_app_role
WITH (security_invoker = on) AS
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
   - `student_profiles`（氏名、電話番号、学生番号、メールアドレス）、`join_requests`（氏名、メールアドレス）、`guild_members`（ユーザー名、表示名）、`member_survey_responses`（学生番号）などは個人情報（PII）です。ログ出力やエラーレスポンスに生値を含めないこと。
   - `discord_id` は個人情報として扱いません。個人情報の範囲とログ・エラーの出力規約の詳細は [logging-and-errors.md](./logging-and-errors.md) を参照してください。
2. **権限判定の原則**:
   - アプリケーション側の権限判定は `v_users_with_app_role` ビューを参照して行います（テーブル直接操作による不整合を防ぐため）。
3. **ロール優先度（Position）**:
   - `role_manifests.position` は Discord のロール階層順序と連動します。Bot による差分同期時に利用されます。
4. **マイグレーション運用**:
   - スキーマ変更時は Alembic マイグレーションスクリプトを作成し、ローカル検証後に CI で整合性を確認してください。
5. **Row Level Security（RLS）**:
   - anon キーはブラウザに公開され PostgREST 経由で `public` スキーマにアクセスできるため、`public` の全テーブルで RLS を有効にします（`0006_enable_row_level_security` が `public` の全テーブルを対象に実行）。
   - Backend は所有者ロールで接続するため RLS の影響を受けません（`FORCE ROW LEVEL SECURITY` は付けない）。
   - テーブルを追加するときは、同じマイグレーション内で `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY` を実行してください。ビューを追加するときは `security_invoker = on` を指定してください。

