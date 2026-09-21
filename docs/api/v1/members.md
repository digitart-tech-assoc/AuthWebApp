# 会員管理・入会費清算 API 仕様 (`/api/v1/members`)

本ドキュメントは、管理者による仮入会者の把握、部費（入会費）支払いの照合・登録、正式メンバー昇格、期限切れロールの自動解除に関する API 仕様です。

---

## GET `/api/v1/members/pre_member/list`

仮入会ロール（`pre_member`）を持つユーザーの一覧と、部費の支払いステータスを取得します。

* **認可レベル**: `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`

### レスポンス (200 OK)
```json
{
  "pre_members": [
    {
      "discord_id": "123456789012345678",
      "username": "taro_yamada",
      "display_name": "山田太郎",
      "avatar": "avatar_hash",
      "assigned_at": "2026-03-25T10:00:00Z",
      "is_paid": true,
      "paid_at": "2026-03-26T14:30:00Z",
      "note": "PayPay支払い確認済み"
    },
    {
      "discord_id": "987654321098765432",
      "username": "hanako_suzuki",
      "display_name": "鈴木花子",
      "avatar": null,
      "assigned_at": "2026-03-27T08:00:00Z",
      "is_paid": false,
      "paid_at": null,
      "note": null
    }
  ]
}
```

---

## POST `/api/v1/members/paid_invitation/register`

管理者が入会費の支払いを確認した際、対象の Discord ID に対して支払い済みレコードを登録します。

* **認可レベル**: `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "discord_id": "123456789012345678",
  "note": "新歓ブースにて現金受取"
}
```

### レスポンス (200 OK)
```json
{
  "ok": true,
  "discord_id": "123456789012345678",
  "result": "registered"
}
```

---

## POST `/api/v1/members/member/add`

管理者がユーザーを正式メンバー（本会員）として承認し、本会員ロールを付与します。

* **認可レベル**: `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "discord_id": "123456789012345678",
  "note": "本入会手続き完了承認"
}
```

### レスポンス (200 OK)
```json
{
  "ok": true,
  "discord_id": "123456789012345678",
  "result": "member_added"
}
```

---

## POST `/api/v1/members/pre_member/cleanup`

仮入会期間（有効期限）が経過したユーザーの仮入会ロールを自動解除し、監査ログ（`pre_member_removal_log`）に記録します。定期実行バッチまたは管理者手動トリガーで実行されます。

* **認可レベル**: `Admin` または `Internal`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>` または `Authorization: Bearer <SHARED_SECRET>`

### レスポンス (200 OK)
```json
{
  "ok": true,
  "removed_count": 3,
  "removed_users": ["123456789012345678", "234567890123456789"]
}
```

---

## POST `/api/v1/members/pre_member/register`

Discord Bot が新規参加者を検知した際に呼び出す内部登録エンドポイント。

* **認可レベル**: `Internal`（`SHARED_SECRET`）
* **リクエストボディ**:
```json
{
  "discord_id": "123456789012345678",
  "source": "P"
}
```
