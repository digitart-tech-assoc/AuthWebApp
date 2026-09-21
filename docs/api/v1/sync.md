# Bot 同期トリガー API 仕様 (`/api/v1/sync`)

本ドキュメントは、バックエンドから Discord Bot の内部受信用エンドポイント（`POST /internal/sync`）へ同期要求を転送する API 仕様です。

---

## POST `/api/v1/sync`

Discord Bot に対し、ロールの差分同期（Reconciliation）の実行を要求します。

* **認可レベル**: `Internal` または `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SHARED_SECRET>` または `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "action": "sync_roles"
}
```

### レスポンス (200 OK)
```json
{
  "ok": true,
  "bot": {
    "status_code": 200,
    "status": "enqueued"
  }
}
```
