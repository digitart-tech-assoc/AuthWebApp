# テーブル使用状況分析レポート

**作成日**: 2026年4月14日  
**対象**: users, guild_members, role_member_assignments, member_list, pre_member_list, admin_list, role_assignments, role_manifests, role_categories, student_profiles, otp_records, otp_codes, join_requests, member_survey_responses, pre_member_removal_log, paid_invitations, audit_logs, events, role_changes

---

## 1. users テーブル

**アクセスレベル**: ⭐⭐⭐ 頻繁  
**主要カラム**: id, user_id (PK/FK to Supabase auth), discord_id, app_role, created_at, updated_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L17) | SELECT | user_id で検索 (`find_user_by_sub`) |
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L77) | SELECT | user_id で検索し app_role 取得 |
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L90) | UPDATE | app_role を更新（role リスト同期時） |
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L126) | UPDATE | discord_id と app_role を更新 |
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L144) | INSERT | 新規ユーザーを作成 |
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L176) | UPDATE | app_role を更新 |

**使用流れ**:  
- Supabase 認証後、user_id で既存ユーザーを検索
- member/admin/pre_member リストから app_role を解決して自動同期
- サインイン時に毎回実行される

---

## 2. guild_members テーブル

**アクセスレベル**: ⭐⭐ 中程度  
**主要カラム**: user_id (PK), username, display_name, avatar, updated_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L416) | DELETE | ギルドメンバー全削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L420) | INSERT | Discord API から取得したメンバーを一括保存 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L552) | SELECT | ギルドメンバー一覧を全取得（role assignment UI 用） |
| [backend/app/api/v1/roles.py](backend/app/api/v1/roles.py#L107) | WRITE | `save_guild_members` で同期 |

**使用流れ**:  
- Discord Bot が `fetch_all_guild_members` で取得したメンバー一覧を保存
- Role assignment UI でメンバーを表示する際に参照
- フルリフレッシュは DELETE してから全件 INSERT（truncate + reload パターン）

---

## 3. role_member_assignments テーブル

**アクセスレベル**: ⭐⭐⭐ 頻繁  
**主要カラム**: role_id, user_id (複合PK)

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L494) | DELETE | 特定ロール ID の割り当てをすべて削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L497) | INSERT | role_id と user_id のペアを追加 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L511) | DELETE | あるロール全体のメンバー削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L514) | INSERT | 新しいメンバーを割り当て |
| [backend/app/db/repository.py](backend/app/db/repository.py#L524) | INSERT | 指定ユーザーをロールに追加 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L535) | DELETE | 指定ユーザーをロールから削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L545) | DELETE | テーブル全削除（完全再取得用） |
| [backend/app/db/repository.py](backend/app/db/repository.py#L563) | SELECT | 全ロール割り当てをマッピングで取得 |
| [backend/app/api/v1/roles.py](backend/app/api/v1/roles.py#L120) | WRITE | `clear_all_role_assignments` で初期化 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L381) | UPDATE | OTP 検証後、member ロール追加＆pre-member ロール削除 |

**使用流れ**:  
- Discord API で各ロールのメンバーを取得
- 差分更新または全更新でマッピングを保存
- Role reassignment や自動同期時に頻繁に使用

---

## 4. member_list テーブル

**アクセスレベル**: ⭐⭐⭐⭐ 最頻繁  
**主要カラム**: id, discord_id (UNIQUE), user_id, assigned_by, assigned_at, created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L49) | SELECT | app_role を解決するために存在確認 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L598) | DELETE | 同期時に全削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L603) | INSERT | ロール情報から新規追加 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L671) | SELECT | メンバーリストを全取得 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L500-L505) | INSERT | OTP 検証後にメンバーを追加 |
| [backend/app/api/v1/members.py](backend/app/api/v1/members.py#L156) | WRITE | `add_to_member_list` で pre-member から昇格 |
| [frontend/src/actions/members.ts](frontend/src/actions/members.ts#L12) | READ | 同期後に件数返却 |
| [discord-bot/app/services/reconcile.py](discord-bot/app/services/reconcile.py#L71) | SELECT | ボット側で member_list を取得して Discord 権限処理 |

**使用流れ**:  
- Discord ロール同期で member_list / admin_list / pre_member_list が更新される
- pre-member が申保完了（OTP 検証）後に member_list に昇格
- アプリの主要な権限判定フロー（member/admin 判定）

---

## 5. pre_member_list テーブル

**アクセスレベル**: ⭐⭐⭐⭐ 最頻繁  
**主要カラム**: id, discord_id (UNIQUE), user_id, assigned_by, assigned_at, created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L53) | SELECT | app_role を解決するために存在確認 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L637) | DELETE | 同期時に全削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L641) | INSERT | Discord pre-member ロール情報から追加 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L678) | SELECT | pre-member リストを全取得 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L132) | SELECT | pre-member 確認 |
| [backend/app/api/v1/members.py](backend/app/api/v1/members.py#L113) | SELECT | pre-member リスト取得（検索オプション付き） |
| [backend/app/db/repository.py](backend/app/db/repository.py#L841) | SELECT | paid_invitations との LEFT JOIN で支払状況判定 |
| [frontend/src/actions/members.ts](frontend/src/actions/members.ts#L26) | READ | マネジメント画面で pre-member リスト表示 |
| [discord-bot/app/services/reconcile.py](discord-bot/app/services/reconcile.py#L72) | SELECT | Discord 権限付与 |
| [discord-bot/app/main.py](discord-bot/app/main.py#L74) | WRITE | 新規参加者を reg前待ちに登録 |

**使用流れ**:  
- Discord の pre-member ロールメンバーを同期
- OTP 検証・支払い確認フロー
- 新規参加の入口

---

## 6. admin_list テーブル

**アクセスレベル**: ⭐⭐ 中程度  
**主要カラム**: id, discord_id (UNIQUE), user_id, assigned_by, assigned_at, created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L45) | SELECT | app_role を解決するために admin 確認 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L617) | DELETE | 同期時に全削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L622) | INSERT | Discord admin ロール情報から追加 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L673) | SELECT | admin リストを全取得 |
| [backend/app/api/v1/members.py](backend/app/api/v1/members.py#L66) | SELECT | member_list 取得エンドポイント |
| [backend/app/api/v1/roles.py](backend/app/api/v1/roles.py#L415) | SELECT | 同期後に件数返却 |

**使用流れ**:  
- Discord admin ロール情報から自動同期
- app_role 解決で最優先チェック（admin > member > pre_member）

---

## 7. role_assignments テーブル

**⚠️ 注記**: このテーブルは **テーブル定義に見つかりません** (repository.py の init_db に作成処理がない)。  
代わりに **role_member_assignments** で機能が実装されている可能性が高い。

---

## 8. role_manifests テーブル

**アクセスレベル**: ⭐⭐⭐ 頻繁  
**主要カラム**: role_id (PK), name, color, hoist, mentionable, permissions, position, category_id, is_managed_by_app, is_our_bot, updated_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L303) | SELECT | ロールマニフェスト取得 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L327) | DELETE | マニフェスト削除（更新時） |
| [backend/app/db/repository.py](backend/app/db/repository.py#L348) | INSERT | ロール情報をマニフェストに保存 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L371) | DELETE | 指定されないロール ID を削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L378) | INSERT | 新ロール追加 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L408) | UPDATE | ロール ID リネーム（Discord 作成後） |
| [backend/app/db/repository.py](backend/app/db/repository.py#L444) | DELETE | PATCH で指定削除ロール削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L470) | INSERT | PATCH で upsert |
| [backend/app/api/v1/manifest.py](backend/app/api/v1/manifest.py#L68) | SELECT | 現在のマニフェスト取得 |
| [backend/app/api/v1/manifest.py](backend/app/api/v1/manifest.py#L100) | WRITE | save_role_assignments 呼び出し |

**使用流れ**:  
- Discord ロール定義をマニフェストに管理
- color, permissions, position など表示・権限情報を保持
- GET マニフェスト、PUT/PATCH マニフェストで管理

---

## 9. role_categories テーブル

**アクセスレベル**: ⭐⭐ 中程度  
**主要カラム**: id (PK), name, display_order, is_collapsed, permissions

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L285) | SELECT | カテゴリ一覧取得 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L328) | DELETE | マニフェスト更新時に削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L333) | INSERT | 新カテゴリ作成 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L446) | DELETE | PATCH で指定削除カテゴリ削除 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L452) | INSERT | PATCH で upsert |

**使用流れ**:  
- ロールをグループ化するためのカテゴリ管理
- UI での表示順序、折りたたみ状態管理

---

## 10. student_profiles テーブル

**アクセスレベル**: ⭐⭐ 中程度  
**主要カラム**: id, discord_id, student_number, name, furigana, department, gender, phone, email_aoyama, created_at, updated_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L161) | SELECT | 既存プロフィール取得 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L450) | SELECT | プロフィール ID 確認 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L459) | UPDATE | プロフィール情報を更新 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L481) | INSERT | 新規プロフィール作成 |

**使用流れ**:  
- 学生登録フロー（POST /api/v1/student/profile）で保存
- 大学メール (email_aoyama) 自動生成
- OTP 検証後に呼び出し

---

## 11. otp_records テーブル

**アクセスレベル**: ⭐⭐ 中程度（古いフロー用）  
**主要カラム**: id, discord_id, email_aoyama, code, attempt_count, verified, expires_at, created_at, verified_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L188) | SELECT | OTP レコード取得 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L279) | INSERT | OTP コード保存 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L321) | SELECT | 最新の未検証 OTP レコード取得 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L361) | UPDATE | 試行回数をインクリメント |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L373) | UPDATE | verified フラグを立て、verified_at を記録 |
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L428) | SELECT | プロフィール作成時に OTP 検証状態確認 |

**使用流れ**:  
- 学生 Discord OTP 認証フロー（student エンドポイント）で使用
- join_requests + otp_codes（新しいシステム）との並行運用の可能性あり

**⚠️ 注記**: このテーブルは repository.py の init_db に CREATE TABLE がない。マイグレーション済みか検討要。

---

## 12. otp_codes テーブル

**アクセスレベル**: ⭐⭐ 中程度（新しいフロー用）  
**主要カラム**: id (PK), join_request_id (FK), code_hash, expires_at, verified_at, attempt_count, created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L1100) | INSERT | OTP コード作成 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L1139) | SELECT | OTP コード検証 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L1168) | UPDATE | 試行回数をインクリメント |
| [backend/app/db/repository.py](backend/app/db/repository.py#L1179) | UPDATE | OTP を検証済みに |
| [backend/app/api/v1/join.py](backend/app/api/v1/join.py#L62) | WRITE | `create_otp_code` で新規コード作成 |
| [backend/app/api/v1/join.py](backend/app/api/v1/join.py) | WRITE | OTP 検証フロー |

**使用流れ**:  
- 新しい join_requests フロー用 OTP
- join_request_id を ForeignKey に持つ設計
- ON DELETE CASCADE で一括削除管理

---

## 13. join_requests テーブル

**アクセスレベル**: ⭐⭐ 中程度（新フロー用）  
**主要カラム**: id (PK), email (UNIQUE), name, form_type, status, metadata, created_at, updated_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L1009) | SELECT | email で既存申請確認 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L1019) | UPDATE | 既存 pending/failed レコード更新 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L1046) | INSERT | 新規 join_request 作成 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L1196) | SELECT | join_request 全情報取得 |
| [backend/app/api/v1/join.py](backend/app/api/v1/join.py) | WRITE | OTP 送信・検証フロー |
| [frontend/src/lib/join.ts](frontend/src/lib/join.ts#L11) | READ | requestOtp 呼び出し |
| [frontend/src/lib/join.ts](frontend/src/lib/join.ts#L31) | READ | verifyOtp 呼び出し |

**使用流れ**:  
- OTP 送信リクエスト（prospective-student, contact）
- メールアドレスベースの申請トラッキング
- status: pending → verified → completed フロー

---

## 14. member_survey_responses テーブル

**アクセスレベル**: ⭐ 稀（調査回答記録用）  
**主要カラム**: id, discord_id, student_number, response_data (JSONB), created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L1233) | INSERT | 調査回答を保存 |

**使用流れ**:  
- members.survey エンドポイント想定
- 調査データを JSONB で保存

---

## 15. pre_member_removal_log テーブル

**アクセスレベル**: ⭐ 稀（監査用）  
**主要カラム**: id, discord_id, source_flow, expired_at, removed_at, reason, created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/db/repository.py](backend/app/db/repository.py#L790) | CREATE TABLE | テーブル作成 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L809) | INSERT | 有効期限切れ pre-member の削除ログ記録 |

**使用流れ**:  
- `cleanup_expired_prospective_members()` で定期実行
- assigned_by = 'P' の prospective members を有効期限で削除

---

## 16. paid_invitations テーブル

**アクセスレベル**: ⭐⭐ 中程度  
**主要カラム**: id, discord_id (UNIQUE), user_id, note, expires_at, assigned_by, assigned_at, created_at

### 使用状況

| ファイル | 操作 | 詳細 |
|---------|-----|------|
| [backend/app/api/v1/student.py](backend/app/api/v1/student.py#L146) | SELECT | 支払済み確認 |
| [backend/app/api/v1/users.py](backend/app/api/v1/users.py#L33) | SELECT | paid_invitations 確認 |
| [backend/app/db/user_repository.py](backend/app/db/user_repository.py#L191) | SELECT | 支払済み確認 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L841) | SELECT | LEFT JOIN で pre_member と結合 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L906) | SELECT | 既存確認 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L914) | INSERT | member_list 追加時に同時登録 |
| [backend/app/db/repository.py](backend/app/db/repository.py#L958) | INSERT | 手動登録エンドポイント |
| [backend/app/api/v1/members.py](backend/app/api/v1/members.py#L173) | WRITE | 支払済みユーザー登録 |

**使用流れ**:  
- pre-member が入会費支払い確認
- admin が手動で登録可能
- pre-member リスト取得時に is_paid フラグ付与

---

## 17. audit_logs テーブル

**アクセスレベル**: ❌ 未実装  
**主要カラム**: (定義なし)

### 使用状況

**見つかりません** - このテーブルは実装されていない可能性が高い

---

## 18. events テーブル

**アクセスレベル**: ❌ 未実装  
**主要カラム**: (定義なし)

### 使用状況

**見つかりません** - このテーブルは実装されていない可能性が高い

---

## 19. role_changes テーブル

**アクセスレベル**: ❌ 未実装  
**主要カラム**: (定義なし)

### 使用状況

**見つかりません** - このテーブルは実装されていない可能性が高い

---

## まとめ

### 実装済みテーブル（13個）

| # | テーブル | 使用頻度 | 主要用途 |
|---|---------|--------|--------|
| 1 | **users** | ⭐⭐⭐ | Supabase auth と Discord ID、app_role のマッピング |
| 2 | **guild_members** | ⭐⭐ | Discord ギルドメンバー情報キャッシュ |
| 3 | **role_member_assignments** | ⭐⭐⭐⭐ | Discord ロール ← → メンバーマッピング |
| 4 | **member_list** | ⭐⭐⭐⭐ | 正会員リスト（Discord ロール連動） |
| 5 | **pre_member_list** | ⭐⭐⭐⭐ | 入会予定者リスト（Discord ロール連動） |
| 6 | **admin_list** | ⭐⭐ | 管理者リスト（Discord ロール連動） |
| 7 | **role_manifests** | ⭐⭐⭐ | ロール定義情報（Discord ロールのメタデータ） |
| 8 | **role_categories** | ⭐⭐ | ロール分類管理 |
| 9 | **student_profiles** | ⭐⭐ | 学生登録フロー用プロフィール |
| 10 | **otp_records** | ⭐⭐ | Discord 学生用 OTP 認証（古いフロー） |
| 11 | **otp_codes** | ⭐⭐ | Join リクエスト用 OTP（新しいフロー） |
| 12 | **join_requests** | ⭐⭐ | Join フロー申請トラッキング |
| 13 | **pre_member_removal_log** | ⭐ | 有効期限切れ pre-member 削除ログ |
| 14 | **paid_invitations** | ⭐⭐ | 入会費支払い済みリスト |
| 15 | **member_survey_responses** | ⭐ | メンバー調査回答 |

### 未実装テーブル（4個）

- **role_assignments** - role_member_assignments で実装
- **audit_logs** - 未実装
- **events** - 未実装
- **role_changes** - 未実装

### アクセスアーキテクチャ

```
Frontend (Next.js)
    ↓
Backend API (FastAPI)
    ├─ auth.ts / middleware.ts
    ├─ actions/members.ts → members API
    ├─ actions/student-registration.ts → student / join API
    └─ app/api/ → Next.js server routes
        ↓
Database Layer (PostgreSQL)
    ├─ repository.py (main data access)
    ├─ user_repository.py (RBAC)
    └─ discord_client.py (Discord API integration)
        ↓
Discord Bot (Standalone)
    └─ reconcile.py → リスト同期
```

### パフォーマンス最適化ポイント

1. **member_list, pre_member_list**: DELETE + INSERT パターン（フルリプレイス）
   - インデックス: discord_id (UNIQUE)
   - 部分検索対応: pre_member_list ILIKE で検索
   
2. **role_member_assignments**: role_id ごとの DELETE + 複数 INSERT
   - 複合キー (role_id, user_id)
   - 差分更新推奨
   
3. **join_requests**: Email UNIQUE 制約
   - pending/failed 状態では再利用（UPDATE）
   - verified/completed では拒否エラー

### 推奨される追加テーブル

- **audit_logs**: admin アクション追跡
- **role_changes**: ロール変更履歴
- **events**: グローバルイベントログ

