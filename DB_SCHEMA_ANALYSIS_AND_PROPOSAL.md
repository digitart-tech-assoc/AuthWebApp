# DB スキーマ分析と最適化提案

**作成日**: 2026年4月14日  
**対象**: AuthWebApp PostgreSQL スキーマ全体  
**目的**: 冗長性排除と正規化による設計の簡潔化

---

## 第1部: 現在のスキーマ問題分析

### 🔴 **問題1: リスト系テーブルの構造重複**

現在3つの独立テーブル存在：
- `member_list` (discord_id, user_id, assigned_by, assigned_at, created_at)
- `pre_member_list` (discord_id, user_id, assigned_by, assigned_at, created_at)  
- `admin_list` (discord_id, user_id, assigned_by, assigned_at, created_at)

**問題点**:
```
✗ 構造がまったく同じ（discord_id, user_id, assigned_by, assigned_at, created_at）
✗ 1ユーザーが複数リストに同時登録される可能性がある
  例: admin_list + member_list に同時に存在 → 一貫性保証がない
✗ 権限判定が複雑: admin_list を先にチェック、次に member_list...のロジック
✗ DELETE WHERE role_id IN (...) のような一括更新が不可能
✗ 権限のバージョニング・監査が難しい
```

**根本原因**: Discord ロール（member, admin, pre-member）を DB リストで模倣しようとしている
- role_member_assignments は Discord-from-authority
- member_list/admin_list/pre_member_list は derived だが独立管理している

---

### 🔴 **問題2: role_member_assignments との冗長性**

`role_member_assignments` (role_id, user_id):
- Discord ロール情報を正規化して保存（1つの事実のソース）
- 最新の state = SELECT role_id="123" FROM role_member_assignments

`member_list / admin_list / pre_member_list`:
- role_member_assignments の result set をテーブル化している
- 毎回全削除 + 全挿入で再構築
- **結果**: 同じ情報が2重に保持されている

```
Discord API → fetch_all_guild_members() 
           → role_member_assignments に INSERT/DELETE
           → sync_member_lists() で member_list/admin_list/pre_member_list に INSERT/DELETE
           
❌ 2段階同期により複雑性が増加
❌ 同期漏れのリスク
```

---

### 🔴 **問題3: users と guild_members の関係不明**

`users` テーブル:
- id (internal UUID)
- user_id (Supabase auth ID)
- discord_id (Discord user ID)
- app_role (member|admin|pre_member|none) ← 計算値？
- created_at, updated_at

`guild_members` テーブル:
- user_id (Discord user ID = PK)
- username, display_name, avatar
- updated_at

**問題点**:
```
✗ PK が異なる: users は内部 UUID, guild_members は Discord user_id
✗ guild_members.user_id と users.discord_id は同じ値だが、FK がない
✗ guild_members は Discord API から dump されたキャッシュだけ
✗ user_id (Supabase) と user_id (Discord) で名前が被っている
✗ users.app_role は毎回 member_list/admin_list/pre_member_list から計算されている
  → 正規化されていない（計算値を保持しない）
```

---

### 🟡 **問題4: OTP フロー の二重実装**

**古いフロー**: `otp_records` (discord_id, email_aoyama, code, verified, ...)
- Discord ID ベース
- simple string code

**新しいフロー**: `join_requests` + `otp_codes`
- email ベース
- code_hash（セキュア）
- join_request_id (FK)

**問題点**:
```
✗ 2つのフロースが並行運用されている
✗ マイグレーション計画が不明確
✗ どちらが main か不確定
✗ コード内で両方が referenced
```

該当ファイル:
- backend/app/api/v1/student.py → otp_records を使用
- backend/app/api/v1/join.py → otp_codes を使用

---

### 🟡 **問題5: 未実装テーブルの存在**

スキーマに定義されているが、コード内で使用されていない:
- `audit_logs` - 監査機能なし
- `events` - event queue なし
- `role_changes` - ロール変更履歴なし  
- `role_assignments` テーブル定義はあるが、role_member_assignments で実装
  
**問題点**:
```
✗ スキーマ汚染
✗ 開発者の混乱（どれを使うべき？）
✗ メンテナンスコスト
```

---

### 🟡 **問題6: student_profiles の位置付けが不明**

`student_profiles` (discord_id, student_number, name, ..., otp_verified, ...):
```
✗ otp_verified フラグを持つが、otp_records/otp_codes との同期方法が不明
✗ profile_submitted_at vs otp_verified_at のセマンティクスが不明
✗ users.app_role との関係が不明
  student_profiles が存在する ≠ member_list に登録されている
```

---

### 🟡 **問題7: paid_invitations の使用パターン**

```sql
-- 現在の使用法
LEFT JOIN paid_invitations pi ON pm.discord_id = pi.discord_id
WHERE pm.assigned_by != 'P' OR (pm.assigned_by = 'P' AND pi.discord_id IS NOT NULL)
```

**問題点**:
```
✗ pre_member_list の一部を filter する目的だが、join 構文が複雑
✗ paid_invitations と pre_member_list の関係が暗黙的
✗ discord_id が UNIQUE だが、複数支払い記録が必要ならコンフリクト
```

---

## 第2部: カラム単位の必要性検証

### users テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | 内部キー |
| user_id | UNIQUE | ✅ 必須 | Supabase auth 連携 |
| discord_id | UNIQUE | ✅ 必須 | Discord 連携 |
| app_role | - | 🔴 削除推奨 | member_list/admin_list から計算可能（正規化違反） |
| created_at | - | ✅ 必須 | 監査 |
| updated_at | - | ⚠️ 活用度低 | 更新トリガー時の記録（使用例少ない） |

**アクション**: `app_role` を削除。権限は view や dedicated 関数で解決する。

---

### guild_members テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| user_id (Discord) | PK | ✅ 必須 | Discord メンバーの事実ソース |
| username | - | ✅ 必須 | UI 表示 |
| display_name | - | ✅ 必須 | UI 表示 |
| avatar | - | ✅ 必須 | UI 表示 |
| updated_at | - | ✅ 必須 | キャッシュ鮮度管理 |

**アクション**: 問題なし。ただし users テーブルとの FK リレーション明確化推奨。

---

### member_list / admin_list / pre_member_list

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | 🔴 削除推奨 | 不要（discord_id が UNIQUE） |
| discord_id | UNIQUE | ✅ 必須 | リスト構築のキー |
| user_id | FK | ⚠️ 条件付き | users と関連付ける場合のみ |
| assigned_by | - | 🟡 低優先 | 監査用（audit_logs として分離可能） |
| assigned_at | - | 🟡 低優先 | 監査用（audit_logs として分離可能） |
| created_at | - | ⚠️ 活用度低 | created_at と assigned_at の意味が重複 |

**統合提案**: 3つのテーブルを 1つの `user_memberships` テーブル統合
- membership_type: 'member' | 'admin' | 'pre_member' | 'obog'
- (discord_id, membership_type) が複合 UNIQUE

---

### role_member_assignments テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| role_id | PK-part | ✅ 必須 | Discord ロール ID（事実のソース） |
| user_id | PK-part | ✅ 必須 | Discord メンバー ID |

**アクション**: 問題なし。user_memberships テーブル構築の事実ソース。

---

### role_manifests テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| role_id | PK | ✅ 必須 | Discord ロール ID |
| name | - | ✅ 必須 | UI 表示 |
| color | - | ✅ 必須 | Discord ロール表現 |
| hoist | - | ✅ 必須 | Discord ロール表現 |
| mentionable | - | ✅ 必須 | Discord ロール表現 |
| permissions | - | ✅ 必須 | Discord ロール表現 |
| position | - | ✅ 必須 | Discord ロール順序 |
| category_id | FK | ✅ 必須 | ロール分類 |
| is_managed_by_app | - | ✅ 必須 | 自動更新対象外フラグ |
| is_our_bot | - | 🟡 不明 | 使用例が見つからない |
| updated_at | - | ✅ 必須 | 同期時刻管理 |

**アクション**: `is_our_bot` の使用例を確認。未使用なら削除。

---

### role_categories テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | カテゴリ ID |
| name | - | ✅ 必須 | UI 表示 |
| display_order | - | ✅ 必須 | 順序管理 |
| is_collapsed | - | ✅ 必須 | UI state |
| created_at | - | ⚠️ 低優先 | 監査用 |
| permissions | - | 🔴 削除推奨 | ロールに permissions があるため不要 |

**アクション**: `permissions` カラムを削除。

---

### student_profiles テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | 内部キー |
| discord_id | UNIQUE | ✅ 必須 | Discord 連携 |
| student_number | - | ✅ 必須 | 大学 ID |
| name, furigana, department | - | ✅ 必須 | ユーザー情報 |
| gender, phone | - | ✅ 必須 | ユーザー情報 |
| email_aoyama | - | ✅ 必須 | 大学メール |
| email_verified | - | ✅ 必須 | メール検証フラグ |
| email_verified_at | - | ✅ 必須 | メール検証日時 |
| otp_verified | - | 🔴 削除推奨 | otp_records/otp_codes状態と重複 |
| otp_verified_at | - | 🔴 削除推奨 | otp_records/otp_codes状態と重複 |
| profile_submitted_at | - | ✅ 必須 | プロフィール提出時刻 |
| updated_at | - | ✅ 必須 | 更新トリッキング |
| created_at | - | ✅ 必須 | 作成トラッキング |

**アクション**: `otp_verified`, `otp_verified_at` を削除。otp_records/otp_codes の verified_at が source of truth。

---

### otp_records テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | OTP レコード ID |
| discord_id | - | 🔴 削除推奨 | join_requests + otp_codes に統一すべき |
| email_aoyama | - | 🔴 削除推奨 | join_requests が email を保有 |
| code | - | 🟡 アーキ次第 | otp_codes に移行時は削除 |
| attempt_count | - | ✅ 必須 | rate limiting |
| verified | - | 🟡 アーキ次第 | otp_codes に移行時は削除 |
| verified_at | - | 🟡 アーキ次第 | otp_codes に移行時は削除 |
| expires_at | - | ✅ 必須 | 有効期限管理 |
| created_at | - | ✅ 必須 | アクティビティ トラッキング |

**アクション**: otp_codes に統一するか、otp_records を完全に削除するか決定が必要。

---

### otp_codes テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | OTP レコード ID |
| join_request_id | FK | ✅ 必須 | join_requests との関連付け |
| code_hash | - | ✅ 必須 | セキュリティ（平文ではなくハッシュ） |
| expires_at | - | ✅ 必須 | 有効期限管理 |
| verified_at | - | ✅ 必須 | 検証日時 |
| attempt_count | - | ✅ 必須 | rate limiting |
| created_at | - | ✅ 必須 | アクティビティ トラッキング |

**アクション**: こちらが新しいフロー。otp_records と統一決定。

---

### join_requests テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | リクエスト ID |
| email | UNIQUE | ✅ 必須 | applicant email |
| name | - | ✅ 必須 | 申請者名 |
| form_type | - | ✅ 必須 | 'prospective-student'\|'contact' |
| status | - | ✅ 必須 | 'pending'\|'verified'\|'completed'\|'failed' |
| metadata | - | ⚠️ 活用度低 | JSON フィールド（拡張性） |
| created_at | - | ✅ 必須 | トラッキング |
| updated_at | - | ✅ 必須 | トラッキング |

**アクション**: 問題なし。otp_codes との関係を強化（FK）。

---

### pre_member_removal_log テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | ログ ID |
| discord_id | - | ✅ 必須 | 誰が削除されたか |
| source_flow | - | ✅ 必須 | 削除原因（有効期限 vs 手動） |
| expired_at | - | ⚠️ null可 | 有効期限切れ日時 |
| removed_at | - | ✅ 必須 | 削除日時 |
| reason | - | 🟡 低優先 | 詳細な理由（自由記述） |
| created_at | - | ✅ 必須 | ログ作成日時 |

**アクション**: 問題なし。

---

### paid_invitations テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | 支払い記録 ID |
| discord_id | UNIQUE | ⚠️ 条件付き | pre_member と 1:1 対応を仮定 |
| user_id | FK | ✅ 必須 | users との関連付け |
| note | - | ✅ 必須 | 支払い方法メモ |
| expires_at | - | ⚠️ 活用度低 | 支払い有効期限？（実装例少ない） |
| assigned_by | - | ✅ 必須 | admin user_id |
| assigned_at | - | ✅ 必須 | 支払い確認日時 |
| created_at | - | ✅ 必須 | レコード作成日 |

**問題**: discord_id UNIQUE が厳しい。複数支払い記録（更新）には対応しない。
**提案**: `status` フィールドを追加（'pending' → 'completed' → 'expired'）

---

### member_survey_responses テーブル

| カラム | 繰度 | 必要性 | 備考 |
|--------|------|--------|------|
| id | PK | ✅ 必須 | 回答 ID |
| profile_id | FK | ✅ 必須 | student_profiles との関連付け |
| student_number | - | 🟡 冗長 | profile_id から student_profiles を JOIN すれば取得可能 |
| join_request_id | FK | 🟡 低優先 | join_requests追跡（複数回答対応？） |
| digitart_channels, circl_search_channels, ... | JSONB | ✅ 必須 | 調査データ |
| raw_payload | JSONB | 🟡 低優先 | デバッグ用（削除も可） |

**アクション**: `student_number` を削除（冗長）。`raw_payload` は必要に応じて。

---

## 第3部: 提案された新スキーマ設計

### 📋 Design Principles

1. **単一事実のソース**  
   - Discord API → role_member_assignments (事実)
   - Supabase → users (認証事実)
   
2. **正規化（第3正規形）**  
   - 計算値（app_role）を保持しない
   - 冗長テーブル（member_list × 3）を統合

3. **명확한 関係性**  
   - FK で テーブル間の関係を明示
   - users.discord_id → guild_members.user_id (FK)

4. **監査可能性（オプション）**  
   - 削除・変更要件に備え、削除マーク（soft delete）を活用
   
5. **保守性**  
   - 未実装テーブル（audit_logs, events, role_changes）は削除

---

### **提案: 統合スキーマ**

```sql
-- ==========================================
-- 1. Core Authentication
-- ==========================================

CREATE TABLE users (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE,  -- Supabase auth user_id
    discord_id TEXT UNIQUE,        -- Discord user_id (nullable初期化時)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
-- Index: user_id (Supabase lookup), discord_id (Discord lookup)


-- ==========================================
-- 2. Discord Integration (Source of Truth)
-- ==========================================

CREATE TABLE guild_members (
    discord_id TEXT PRIMARY KEY,  -- Discord user_id
    username TEXT NOT NULL,
    display_name TEXT,
    avatar TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    -- FOREIGN KEY には未実装 (Discord ID の完全性は Discord API で管理)
);
-- 役割: Discord API から定期 dump。users.discord_id の参考 table


CREATE TABLE role_manifests (
    role_id TEXT PRIMARY KEY,  -- Discord role_id
    name TEXT NOT NULL,
    color TEXT DEFAULT '#000000',
    hoist BOOLEAN DEFAULT false,
    mentionable BOOLEAN DEFAULT false,
    permissions BIGINT DEFAULT 0,
    position INTEGER NOT NULL,
    category_id TEXT,  -- FK role_categories
    is_managed_by_app BOOLEAN DEFAULT true,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    FOREIGN KEY (category_id) REFERENCES role_categories(id) ON DELETE SET NULL
);


CREATE TABLE role_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    is_collapsed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);


CREATE TABLE role_member_assignments (
    role_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,  -- ⭐ Changed: Discord user_id
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (role_id, discord_id),
    FOREIGN KEY (role_id) REFERENCES role_manifests(role_id) ON DELETE CASCADE,
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id) ON DELETE CASCADE
);
-- 役割: Discord ロール ← → メンバー マッピング（事実のソース）
-- 毎回 Discord API から complete reload


-- ==========================================
-- 3. Application User Memberships
-- ==========================================

CREATE TABLE user_memberships (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT NOT NULL,
    membership_type TEXT NOT NULL CHECK (membership_type IN ('member', 'admin', 'pre_member', 'obog')),
    -- Derived from role_member_assignments, but denormalized for query speed
    -- Used for app-level permission checks
    assigned_by TEXT,  -- users.user_id (admin who assigned)
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (discord_id, membership_type),
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id) ON DELETE CASCADE
);
-- 役割: member_list + admin_list + pre_member_list + obog の unified table
-- イベント: sync_member_lists() で role_member_assignments から生成（full replace）
-- Query: WHERE membership_type = 'member' AND ... (権限判定高速化)


-- ==========================================
-- 4. User Registration Flow
-- ==========================================

CREATE TABLE join_requests (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    form_type TEXT NOT NULL CHECK (form_type IN ('prospective-student', 'contact')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'completed', 'failed')),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);


CREATE TABLE otp_codes (
    id TEXT PRIMARY KEY,
    join_request_id TEXT NOT NULL UNIQUE,
    code_hash TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    FOREIGN KEY (join_request_id) REFERENCES join_requests(id) ON DELETE CASCADE
);
-- 役割: join_requests のOTP管理
-- アキテクチャ: 新しい統一フロー（otp_records は削除予定）


CREATE TABLE student_profiles (
    id TEXT PRIMARY KEY,
    discord_id TEXT NOT NULL UNIQUE,
    student_number TEXT NOT NULL,
    name TEXT NOT NULL,
    furigana TEXT NOT NULL,
    department TEXT NOT NULL,
    gender TEXT,
    phone TEXT NOT NULL,
    email_aoyama TEXT NOT NULL DEFAULT '',
    email_verified BOOLEAN NOT NULL DEFAULT false,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    profile_submitted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    -- Removed: otp_verified, otp_verified_at (use otp_codes.verified_at)
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id) ON DELETE CASCADE
);


-- ==========================================
-- 5. Payment & Enrollment
-- ==========================================

CREATE TABLE paid_invitations (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired')),
    assigned_by TEXT NOT NULL,  -- users.user_id
    note TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id) ON DELETE CASCADE
);
-- 変更: discord_id UNIQUE 削除 → status フィールド追加
-- 理由: 複数バージョンの支払い記録に対応（更新・キャンセル etc）
-- Index: (discord_id, status) for query: "latest paid status"


CREATE TABLE member_survey_responses (
    id BIGINT PRIMARY KEY DEFAULT nextval('member_survey_responses_id_seq'::regclass),
    profile_id TEXT NOT NULL,
    digitart_channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    digitart_channels_other TEXT,
    circle_search_channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    circle_search_other TEXT,
    discord_invite_source TEXT,
    discord_invite_other TEXT,
    interested_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    interested_fields_other TEXT,
    motivations JSONB NOT NULL DEFAULT '[]'::jsonb,
    motivations_other TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    -- Removed: join_request_id (join flow が確定していないため), raw_payload, student_number (冗長)
    FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE
);


-- ==========================================
-- 6. Activity & Cleanup Tracking
-- ==========================================

CREATE TABLE pre_member_removal_log (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT NOT NULL,
    source_flow TEXT,
    expired_at TIMESTAMP WITH TIME ZONE,
    removed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id) ON DELETE CASCADE
);


-- ==========================================
-- 7. Cleanup: 削除対象テーブル群
-- ==========================================

-- DELETE: member_list (user_memberships に統合)
-- DELETE: admin_list (user_memberships に統合)
-- DELETE: pre_member_list (user_memberships に統合)
-- DELETE: otp_records (otp_codes に統一)
-- DELETE: role_assignments (role_member_assignments で実装)
-- DELETE: audit_logs (未実装)
-- DELETE: events (未実装)
-- DELETE: role_changes (未実装)
```

---

## 第4部: マイグレーション戦略

### フェーズ1: 準備（破壊的変更前）

```sql
-- 1. user_memberships テーブル作成
CREATE TABLE user_memberships (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT NOT NULL UNIQUE,
    membership_type TEXT NOT NULL,
    assigned_by TEXT,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (discord_id, membership_type),
    FOREIGN KEY (discord_id) REFERENCES guild_members(discord_id)
);

-- 2. users テーブルから app_role 削除
ALTER TABLE users DROP COLUMN app_role;

-- 3. role_member_assignments に assigned_at を追加（オプション、監査用）

-- 4. student_profiles から otp_verified, otp_verified_at 削除
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified;
ALTER TABLE student_profiles DROP COLUMN IF EXISTS otp_verified_at;

-- 5. paid_invitations を修正
ALTER TABLE paid_invitations DROP CONSTRAINT IF EXISTS "paid_invitations_discord_id_key";
ALTER TABLE paid_invitations ADD COLUMN status TEXT DEFAULT 'completed';
ALTER TABLE paid_invitations ADD CONSTRAINT paid_invitations_status_check 
    CHECK (status IN ('pending', 'completed', 'expired'));
```

### フェーズ2: データマイグレーション

```sql
-- 1. member_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT discord_id, 'member', assigned_by, assigned_at, created_at
FROM member_list;

-- 2. admin_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT discord_id, 'admin', assigned_by, assigned_at, created_at
FROM admin_list;

-- 3. pre_member_list → user_memberships
INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
SELECT discord_id, 'pre_member', assigned_by, assigned_at, created_at
FROM pre_member_list;
```

### フェーズ3: 旧テーブル削除

```sql
-- 旧テーブル削除（バックアップ後）
DROP TABLE member_list;
DROP TABLE admin_list;
DROP TABLE pre_member_list;
DROP TABLE otp_records;  -- otp_codes に統一した場合
DROP TABLE role_assignments;  -- role_member_assignments で実装
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS role_changes;
```

---

## 第5部: 実装への影響分析

### ✅ メリット

| 項目 | 効果 |
|------|------|
| **テーブル数削減** | 25 → 16（9個削減） |
| **冗長性排除** | member_list × 3 → user_memberships 1つ |
| **正規化** | 計算値（app_role）削除 |
| **FK 明確化** | guild_members ← users 関係を自動整合 |
| **クエリ簡潔化** | member_list/admin_list/pre_member_list のUNION不要 |
| **スキーマ保守性** | 未実装テーブルの削除で mixed signals 排除 |

### ⚠️ 変更が必要な実装

| ファイル | 変更内容 |
|---------|---------|
| user_repository.py | app_role 計算ロジック追加（app_role = CASE WHEN ... membership_type） |
| repository.py | sync_member_lists() → user_memberships に INSERT（同じロジック） |
| roles.py (API) | 変更なし（SQL が若干簡潔に） |
| discord_client.py | 変更なし（role_member_assignments アクセスは同じ） |
| reconcile.py | user_memberships から pre_member を読むように変更 |
| student.py | otp_verified_at の削除対応 |
| join.py | 変更なし（otp_codes は既に統合） |

### ⚠️ 実装難度

- **低**: paid_invitations に status カラム追加
- **中**: user_memberships テーブル作成 + データマイグレーション
- **中**: user_repository の app_role 計算ロジック
- **高**: otp_records → otp_codes の統一（binary compatibility 確認）

---

## 第6部: 推奨実装順序

1. **Phase 1: スキーマ拡張（非破壊）**
   - user_memberships テーブル作成
   - 既存テーブルの外部制約確認

2. **Phase 2: 新コード実装**
   - user_repository の app_role CASE WHEN 実装
   - sync_member_lists() → user_memberships + INTO の dual write

3. **Phase 3: データマイグレーション**
   - member_list → user_memberships へのコピー
   - キーワード: blue-green deployment or maintenance window

4. **Phase 4: 旧テーブル削除**
   - コード内の参照を user_memberships に切り替え
   - member_list/admin_list/pre_member_list テーブル削除

5. **Phase 5: OTP フロー統一（オプション）**
   - otp_records を完全削除 or 並行運用継続
   - decide migrate timeline based on business needs

---

## 結論

### 現在のスキーマの主な課題

1. ❌ member_list × 3 の冗長テーブル
2. ❌ role_member_assignments との自同期
3. ❌ app_role 正規化違反
4. ❌ guild_members と users の関係がFK化されていない
5. ❌ otp_records と otp_codes の二重実装
6. ❌ 未実装テーブルによるスキーマ汚染

### 提案スキーマのメリット

✅ テーブル数削減（25 → 16）  
✅ 冗長性完全排除  
✅ 第三正規形達成  
✅ FK による自動整合  
✅ クエリ簡潔化  
✅ 保守性向上  

### 推奨アクション

- **破壊的変更OK**: Phase 1 ～ 4 実装を推奨
- **段階的実装**: Phase 1-2 を先に、Phase 3-4 は次の release
- **OTP 統一**: ビジネス需要に応じて Phase 5

