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

## POST `/api/v1/roles/self-assign`

ログインメンバーが、自分自身に対してロールを付与します。
※管理者が保護しているカテゴリ（`is_restricted: true`）に属するロールは付与できません。

* **認可レベル**: `Member`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "role_id": "123456789012345678"
}
```

### レスポンス (200 OK)
```json
{
  "ok": true,
  "message": "Role assigned successfully",
  "role_id": "123456789012345678"
}
```

---

## POST `/api/v1/roles/self-remove`

ログインメンバーが、自分自身からロールを解除します。

* **認可レベル**: `Member`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "role_id": "123456789012345678"
}
```

### レスポンス (200 OK)
```json
{
  "ok": true,
  "message": "Role removed successfully",
  "role_id": "123456789012345678"
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
