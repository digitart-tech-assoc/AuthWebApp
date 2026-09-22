# API 仕様（FastAPI Backend）

本ドキュメントは、**Digitart サークル認証システム** のバックエンド（FastAPI）が提供する REST API（`/api/v1`）の公式仕様書です。
フロントエンド（Next.js）および Discord Bot は、この API を介して DB アクセスやロール同期を行います。

---

## 1. 認証・認可アーキテクチャ

### 認証ヘッダー
API リクエスト時は、`Authorization` ヘッダーに以下のいずれかを付与します。

1. **ユーザー認証（Frontend -> Backend）**:
   ```http
   Authorization: Bearer <SUPABASE_JWT_TOKEN>
   ```
   - Supabase Auth のセッション JWT を検証します（JWKS 公開鍵または `SUPABASE_JWT_SECRET` による検証）。
   - JWT のクレーム（`sub`、`identities`、`app_metadata`）から安全に `discord_id` を特定します。
   - `v_users_with_app_role` ビューを参照し、有効な `app_role`（`admin`, `member`, `obog`, `pre_member`, `none`）を動的に解決します。

2. **内部・サービス間認証（Discord Bot / 内部バッチ -> Backend）**:
   ```http
   Authorization: Bearer <SHARED_SECRET>
   ```
   - 内部連携用の共有シークレットによる認証です。`app_role: "admin"` 相当の権限として扱われます。

### 認可レベル（アクセス制御）
各エンドポイントには以下の認可レベルが設定されています：

| レベル | 対象ユーザー | 認可失敗時 |
| :--- | :--- | :--- |
| **Public** | 誰でもアクセス可能（未認証可） | - |
| **Authenticated** | ログイン済みユーザー（`get_current_principal`） | `401 Unauthorized` |
| **Member** | `member`, `sub_user`, `obog`, `admin` のいずれか | `403 Forbidden` |
| **Admin** | `admin` ロールのみ（`require_admin`） | `403 Forbidden` |
| **Internal** | `SHARED_SECRET` による内部通信のみ | `401 Unauthorized` / `403 Forbidden` |

---

## 2. API リソース一覧（詳細仕様へのリンク）

詳細なリクエスト/レスポンススキーマは、各リソースの仕様書を参照してください。

| リソース | ベースパス | 説明 | 詳細仕様書 |
| :--- | :--- | :--- | :--- |
| **ユーザー・認証** | `/api/v1/auth` | ログイン直後の同期、現在のユーザー情報・ロール取得 | [v1/auth.md](./v1/auth.md) |
| **ロール・マニフェスト** | `/api/v1/manifest`, `/api/v1/roles` | ロール定義の取得・一括/差分保存、Discord同期、セルフロール操作 | [v1/manifest.md](./v1/manifest.md) / [v1/roles.md](./v1/roles.md) |
| **会員管理・入会費清算** | `/api/v1/members` | 仮入会者一覧、入会費支払い照合・承認、正式メンバー追加 | [v1/members.md](./v1/members.md) |
| **入会申請・OTP認証** | `/api/v1/join` | 入学見込み生等の仮入会申請、ワンタイムパスワード（OTP）検証 | [v1/join.md](./v1/join.md) |
| **在学生登録・学生認証** | `/api/v1/student` | 本入会適格性チェック、大学メール認証、学生プロフィール管理 | [v1/student.md](./v1/student.md) |
| **入会アンケート** | `/api/v1/survey` | 本入会フォームで入力されたアンケート回答データの保存 | [v1/survey.md](./v1/survey.md) |
| **お問い合わせ** | `/api/v1/contact` | 問い合わせ受付、Discord チャンネルへの通知 | [v1/contact.md](./v1/contact.md) |
| **Bot同期トリガー** | `/api/v1/sync` | Discord Bot への即時同期命令の発行 | [v1/sync.md](./v1/sync.md) |
| **開発用ツール** | `/api/v1/dev` | 開発環境での一時的ロール切替（本番環境では自動無効化） | [v1/dev.md](./v1/dev.md) |

---

## 3. 全エンドポイント一覧表

### 3.1. ユーザー・認証 (`/api/v1/auth`)
- `POST /api/v1/auth/login-or-register` (Authenticated): ログイン直後同期・ロール返却 → [詳細](./v1/auth.md#post-apiv1authlogin-or-register)
- `GET /api/v1/auth/me` (Authenticated): ログインユーザー情報取得 → [詳細](./v1/auth.md#get-apiv1authme)
- `GET /api/v1/auth/role-by-sub` (Internal): sub からロール取得 → [詳細](./v1/auth.md#get-apiv1authrole-by-sub)

### 3.2. マニフェスト・ロール (`/api/v1/manifest`, `/api/v1/roles`)
- `GET /api/v1/manifest` (Member): 宣言型ロールマニフェスト取得 → [詳細](./v1/manifest.md#get-apiv1manifest)
- `PUT /api/v1/manifest` (Admin): マニフェスト一括更新 → [詳細](./v1/manifest.md#put-apiv1manifest)
- `PATCH /api/v1/manifest` (Admin): マニフェスト差分更新 → [詳細](./v1/manifest.md#patch-apiv1manifest)
- `POST /api/v1/roles/refresh` (Member): Discordから最新ロール/メンバーをDB同期 → [詳細](./v1/roles.md#post-apiv1rolesrefresh)
- `POST /api/v1/roles/push` (Admin): DBのロール定義をDiscordへ反映 → [詳細](./v1/roles.md#post-apiv1rolespush)
- `POST /api/v1/roles/self-assign` (Member): 自身のロール付与 → [詳細](./v1/roles.md#post-apiv1rolesself-assign)
- `POST /api/v1/roles/self-remove` (Member): 自身のロール解除 → [詳細](./v1/roles.md#post-apiv1rolesself-remove)
- `GET /api/v1/roles/lists` (Member): 管理ロール名・メンバー一覧取得 → [詳細](./v1/roles.md#get-apiv1roleslists)
- `GET /api/v1/roles/members` (Member): 指定ロールの所属メンバー一覧 → [詳細](./v1/roles.md#get-apiv1rolesmembers)
- `POST /api/v1/roles/members/sync` (Admin): 特定ロールのメンバー割当同期 → [詳細](./v1/roles.md#post-apiv1rolesmemberssync)
- `PATCH /api/v1/roles/{role_id}/permissions` (Admin): 権限フラグ直接更新 → [詳細](./v1/roles.md#patch-apiv1rolesrole_idpermissions)
- `GET /api/v1/roles/debug/guilds` (Internal): Bot参加ギルド一覧 → [詳細](./v1/roles.md#get-apiv1rolesdebugguilds)

### 3.3. メンバー管理・入会費清算 (`/api/v1/members`)
- `GET /api/v1/members/pre_member/list` (Admin): 仮入会者・入会費支払い状態一覧 → [詳細](./v1/members.md#get-apiv1memberspre_memberlist)
- `POST /api/v1/members/paid_invitation/register` (Admin): 入会費支払い登録・承認 → [詳細](./v1/members.md#post-apiv1memberspaid_invitationregister)
- `POST /api/v1/members/member/add` (Admin): 正式メンバー登録・ロール付与 → [詳細](./v1/members.md#post-apiv1membersmemberadd)
- `POST /api/v1/members/pre_member/register` (Internal): Botからの仮入会登録 → [詳細](./v1/members.md#post-apiv1memberspre_memberregister)
- `POST /api/v1/members/pre_member/cleanup` (Admin/Internal): 期限切れ仮入会ロールの一括自動解除 → [詳細](./v1/members.md#post-apiv1memberspre_membercleanup)
- `GET /api/v1/members/internal/lists` (Internal): 内部用メンバーIDリスト照会 → [詳細](./v1/members.md#get-apiv1membersinternallists)

### 3.4. 入会申請・仮入会 OTP 認証 (`/api/v1/join`)
- `POST /api/v1/join/request` (Public): 仮入会申請・OTPメール送信 → [詳細](./v1/join.md#post-apiv1joinrequest)
- `POST /api/v1/join/verify` (Public): OTP検証・Discord招待リンク返却 → [詳細](./v1/join.md#post-apiv1joinverify)

### 3.5. 在学生登録・学生認証 (`/api/v1/student`)
- `POST /api/v1/student/validate-eligibility` (Authenticated): 本入会適格性の事前判定 → [詳細](./v1/student.md#post-apiv1studentvalidate-eligibility)
- `POST /api/v1/student/otp/send` (Authenticated): 大学メール宛 OTP 送信 → [詳細](./v1/student.md#post-apiv1studentotpsend)
- `POST /api/v1/student/otp/verify` (Authenticated): 大学メール OTP 検証 → [詳細](./v1/student.md#post-apiv1studentotpverify)
- `GET /api/v1/student/profile` (Authenticated): 学生プロフィール取得 → [詳細](./v1/student.md#get-apiv1studentprofile)
- `POST /api/v1/student/profile` (Authenticated): 学生プロフィール登録・更新 → [詳細](./v1/student.md#post-apiv1studentprofile)

### 3.6. 入会アンケート (`/api/v1/survey`)
- `POST /api/v1/survey/` (Authenticated): アンケート回答保存 → [詳細](./v1/survey.md#post-apiv1survey)

### 3.7. お問い合わせ (`/api/v1/contact`)
- `POST /api/v1/contact/submit` (Public): 問い合わせ受付・Discordチャンネル通知 → [詳細](./v1/contact.md#post-apiv1contactsubmit)

### 3.8. Bot 同期トリガー (`/api/v1/sync`)
- `POST /api/v1/sync` (Internal/Admin): Discord Bot 同期通知 → [詳細](./v1/sync.md#post-apiv1sync)

### 3.9. 開発用ツール (`/api/v1/dev` ※開発環境限定)
- `GET /api/v1/dev/state` (Authenticated): 開発用ロール状態取得 → [詳細](./v1/dev.md#get-apiv1devstate)
- `POST /api/v1/dev/switch-role` (Authenticated): 開発用ロール切替 → [詳細](./v1/dev.md#post-apiv1devswitch-role)

### 3.10. システムヘルスチェック
- `GET /health` (Public): 稼働確認 (`{"status": "ok"}`)

---

## 4. 共通エラーハンドリング

API は標準的な HTTP ステータスコードと JSON 形式のエラーレスポンスを返却します。

```json
{
  "detail": "エラーの詳細メッセージ"
}
```

### 主なステータスコード
- `400 Bad Request`: リクエストパラメータ不正、バリデーションエラー
- `401 Unauthorized`: 認証トークン欠落、無効な JWT、期限切れ
- `403 Forbidden`: 権限不足（管理者限定操作、メンバー限定操作へのアクセス拒否）
- `404 Not Found`: 指定リソースが存在しない
- `422 Unprocessable Entity`: Pydantic スキーマ違反
- `500 Internal Server Error`: サーバー内部エラー
- `502 Bad Gateway`: Discord API や Discord Bot との通信失敗
