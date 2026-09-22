# ロール操作 API 仕様 (`/api/v1/roles`)

本ドキュメントは、Discord ロールの取得、Discord への同期（Push）、セルフロール付与・解除、権限変更に関する API 仕様です。

---

## POST `/api/v1/roles/refresh`

Discord API を直接呼び出して最新のロール一覧およびサーバー参加メンバーを取得し、DB（`role_manifests`, `guild_members`, `role_member_assignments`）へ同期・上書きします。

* **認可レベル**: `Member`（`member`, `sub_user`, `obog`, `admin`）
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**: なし

### レスポンス (200 OK)
```json
{
  "ok": true,
  "guild_id": "1488327535132413974",
  "roles": 32,
  "members": 150
}
```

---

## POST `/api/v1/roles/push`

DB 上で編集されたロール定義（Desired State）を Discord サーバーへ実際に適用（作成・更新・削除・並び順調整）します。また、完了時に Discord Bot へ同期通知を発行します。

* **認可レベル**: `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "desired_roles": [
    {
      "role_id": "123456789012345678",
      "name": "2024年度生",
      "color": "#3498DB",
      "hoist": false,
      "mentionable": false,
      "permissions": 0,
      "position": 15
    }
  ]
}
```

### レスポンス (200 OK)
```json
{
  "ok": true,
  "created": 1,
  "updated": 2,
  "deleted": 0,
  "reordered": 15
}
```

---

## POST `/api/v1/roles/self-batch`

ログインメンバーが、自分自身のロールを一括で付与・解除（バッチ更新）します。
Discord REST API のメンバーロール更新（`PATCH /guilds/{guild_id}/members/{user_id}`）および DB の割り当て更新を 1 回のリクエストでアトミックに適用します。

* **認可レベル**: `Member` (`member`, `admin`, `obog`)
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "roles_to_add": ["123456789012345678"],
  "roles_to_remove": ["234567890123456789"]
}
```
※ `roles_to_add` と `roles_to_remove` はそれぞれ最大50件まで指定可能です。

### レスポンス (200 OK)
```json
{
  "ok": true,
  "discord_id": "123456789012345678",
  "added": ["123456789012345678"],
  "removed": ["234567890123456789"]
}
```
変更がなかった場合:
```json
{
  "ok": true,
  "added": [],
  "removed": [],
  "detail": "変更点はありませんでした"
}
```

### バリデーション & エラーレスポンス
- `400 Bad Request`:
  - 同一ロールが `roles_to_add` と `roles_to_remove` の両方に指定されている場合
  - Discord ID が特定できない場合
- `403 Forbidden`:
  - 管理者保護カテゴリ（`is_restricted: true` または予約カテゴリ）に属するロールが含まれる場合
  - Discord のマネージドロール（Bot/連携用）または `@everyone` ロールが含まれる場合
  - Bot の権限階層以上のロールが含まれる場合
- `404 Not Found`:
  - 指定されたロールがマニフェストまたは Discord サーバー上に存在しない場合
  - ギルドメンバーが見つからない場合
- `500 Internal Server Error`:
  - DB更新失敗時。Discord 上のロール変更は元の状態に自動補償ロールバックされます。
- `502 Bad Gateway`:
  - Discord API との通信エラー。

---

## 【廃止】POST `/api/v1/roles/self-assign` / `/api/v1/roles/self-remove`

旧セルフロール単一操作 API です。本 API は廃止されており、常に `410 Gone` を返却します。
一括更新 API（`POST /api/v1/roles/self-batch`）を使用してください。

* **ステータスコード**: `410 Gone`
* **レスポンス**:
```json
{
  "detail": "This endpoint has been deprecated and removed. Please use POST /api/v1/roles/self-batch instead."
}
```


---

## GET `/api/v1/roles/lists`

環境変数で設定された管理対象ロール（`member`, `admin`, `pre_member`, `obog`）の名前設定およびメンバー一覧を取得します。

* **認可レベル**: `Member`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`

### レスポンス (200 OK)
```json
{
  "admin_role_names": ["Admin", "運営"],
  "member_role_names": ["Member", "部員"],
  "obog_role_names": ["OB/OG"],
  "pre_member_role_name": "仮入会",
  "restricted_categories": ["会員情報", "学年"]
}
```

---

## GET `/api/v1/roles/members`

指定したロール ID に所属しているメンバーの一覧を取得します。

* **認可レベル**: `Member`
* **クエリパラメータ**: `role_id` (string, 必須)

### レスポンス (200 OK)
```json
{
  "role_id": "123456789012345678",
  "members": [
    {
      "user_id": "discord_user_id_1",
      "username": "taro_yamada",
      "display_name": "山田太郎",
      "avatar": "avatar_hash"
    }
  ]
}
```

---

## POST `/api/v1/roles/members/sync`

特定ロールに所属するメンバーの割当を、Discord の実態から DB へ同期します。

* **認可レベル**: `Admin`
* **リクエストボディ**: `{"role_id": "123456789012345678"}`

---

## PATCH `/api/v1/roles/{role_id}/permissions`

ロールの Discord 権限ビットフラグを更新します。

* **認可レベル**: `Admin`
* **パスパラメータ**: `role_id` (string)
* **リクエストボディ**:
```json
{
  "permissions": 8
}
```
