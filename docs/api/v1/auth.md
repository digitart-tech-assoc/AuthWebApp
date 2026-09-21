# ユーザー・認証 API 仕様 (`/api/v1/auth`)

本ドキュメントは、ログイン後のユーザー同期、現在のセッション情報照会、内部向けロール取得に関する API 仕様です。

---

## POST `/api/v1/auth/login-or-register`

ログイン直後にフロントエンドから呼び出され、Supabase Auth ユーザーをバックエンドの `users` テーブルへ同期・登録し、最新のロール情報を返却します。

* **認可レベル**: `Authenticated`（Supabase JWT 必須）
* **リクエストヘッダー**:
  ```http
  Authorization: Bearer <SUPABASE_JWT_TOKEN>
  ```
* **リクエストボディ**: なし

### レスポンス (200 OK)
```json
{
  "sub": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "discord_id": "123456789012345678",
  "app_role": "member",
  "is_paid": true,
  "display_name": null,
  "avatar": null
}
```

---

## GET `/api/v1/auth/me`

現在のログインユーザーの情報、有効なロール、入会費支払い状態、Discord 表示名・アバター情報を取得します。

* **認可レベル**: `Authenticated`（Supabase JWT 必須）
* **リクエストヘッダー**:
  ```http
  Authorization: Bearer <SUPABASE_JWT_TOKEN>
  ```
* **リクエストボディ**: なし

### レスポンス (200 OK)
```json
{
  "sub": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "discord_id": "123456789012345678",
  "app_role": "member",
  "is_paid": true,
  "display_name": "山田太郎",
  "avatar": "a_1234567890abcdef"
}
```

* `app_role` の値: `"admin"`, `"member"`, `"obog"`, `"pre_member"`, `"none"`

---

## GET `/api/v1/auth/role-by-sub`

内部サービス（Discord Bot や内部バッチ）向けに、指定した Supabase `sub`（UUID）のロール・支払い状態を取得します。

* **認可レベル**: `Internal`（`SHARED_SECRET` 必須）
* **リクエストヘッダー**:
  ```http
  Authorization: Bearer <SHARED_SECRET>
  ```
* **クエリパラメータ**:
  | パラメータ | 型 | 必須 | 説明 |
  | :--- | :--- | :---: | :--- |
  | `sub` | string | ○ | 照会対象の Supabase ユーザー UUID |

### レスポンス (200 OK)
```json
{
  "sub": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "discord_id": "123456789012345678",
  "app_role": "admin",
  "is_paid": false,
  "display_name": null,
  "avatar": null
}
```
