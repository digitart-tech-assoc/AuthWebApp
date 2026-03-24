# DB 設計（PostgreSQL）

以下は本プロジェクトの主要テーブルの DDL（初期案）です。運用時は Alembic 等でマイグレーション管理してください。

```sql
-- role_categories: ロールをグループ化する論理単位
CREATE TABLE role_categories (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  display_order INTEGER DEFAULT 0,
  is_collapsed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- role_manifests: 宣言型（Desired State）のロール定義
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
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- events: アウトボックスパターンで Backend -> Bot の命令を受け渡す
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  priority INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  claimed_by TEXT,
  claim_expires_at TIMESTAMPTZ,
  retry_count INTEGER DEFAULT 0,
  last_error TEXT,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- audit_logs: 監査ログ（PII を含めない）
CREATE TABLE audit_logs (
  id TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  actor_id TEXT,
  target_id TEXT,
  target_type TEXT,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 将来拡張: users, student_infos, applications
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  discord_id TEXT UNIQUE NOT NULL,
  email TEXT,
  is_alumni BOOLEAN DEFAULT FALSE,
  withdrawn_at TIMESTAMPTZ,
  data_retention_until TIMESTAMPTZ,
  deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE student_infos (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  student_no TEXT,
  name TEXT,
  furigana TEXT,
  gender TEXT,
  phone TEXT,
  degree_code INTEGER,
  entry_year INTEGER,
  graduation_date TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  is_current BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- インデックス
CREATE INDEX idx_events_status_priority ON events(status, priority, created_at);
CREATE INDEX idx_audit_logs_target ON audit_logs(target_type, target_id);
```

## 運用ルール（DB）
- `events.payload` に PII を含めないこと（ID のみ）。
- `role_manifests.position` は Discord の優先順位に対応する絶対値。Bot は position の値を用いて Discord 側の並びを調整する。
- マイグレーションは必ず CI で実行し、本番前にスキーマ互換を確認する。
