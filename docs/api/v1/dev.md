# 開発用ロール切替 API 仕様 (`/api/v1/dev`)

本ドキュメントは、ローカル開発およびステージング環境において、フロントエンドの `DevRoleSwitcher` コンポーネント等から呼び出されるロール切替ツールの API 仕様です。

> [!WARNING]
> **本番環境での自動遮断**:
> 本 API は `FASTAPI_ENV` が開発用値（`development`, `dev`, `local`）に設定されている場合のみ有効化されます。本番環境（`production`）では多層防御により `404 Not Found` が返却され、API ルート自体が無効化されます。

---

## GET `/api/v1/dev/state`

現在ログインしている開発ユーザーのロール、支払い状態、および利用可能なロール一覧を取得します。

* **認可レベル**: `Authenticated`（開発環境のみ）
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`

### レスポンス (200 OK)
```json
{
  "discord_id": "123456789012345678",
  "current_role": "member",
  "is_paid": true,
  "available_roles": ["admin", "member", "pre_member", "obog", "sub_user", "none"]
}
```

---

## POST `/api/v1/dev/switch-role`

現在ログインしている開発ユーザーのロールおよび部費支払い状態を一時的に変更します。

* **認可レベル**: `Authenticated`（開発環境のみ）
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "role": "admin",
  "is_paid": true
}
```

### レスポンス (200 OK)
```json
{
  "success": true,
  "discord_id": "123456789012345678",
  "new_role": "admin",
  "is_paid": true,
  "message": "Role successfully switched to admin"
}
```
