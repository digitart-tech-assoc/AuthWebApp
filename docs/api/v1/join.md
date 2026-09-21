# 入会申請・仮入会 OTP 認証 API 仕様 (`/api/v1/join`)

本ドキュメントは、入学見込み生等の仮入会申請、ワンタイムパスワード（OTP）送信、および認証コード検証に関する API 仕様です。

---

## POST `/api/v1/join/request`

仮入会申請を受け付け、指定されたメールアドレス宛に 6 桁のワンタイムパスワード（OTP）を送信します。

* **認可レベル**: `Public`（未認証でアクセス可能）
* **制限事項**: `form_type == "prospective-student"` の場合、受付期間（毎年2月1日～4月5日）外は `403 Forbidden` を返します。
* **リクエストボディ**:
```json
{
  "email": "prospective@example.com",
  "confirm_email": "prospective@example.com",
  "name": "青山 太郎",
  "form_type": "prospective-student",
  "metadata": {
    "high_school": "青学高等部",
    "faculty": "理工学部"
  }
}
```

### レスポンス (200 OK)
```json
{
  "id": "req-uuid-1234-5678",
  "email": "prospective@example.com",
  "name": "青山 太郎",
  "form_type": "prospective-student",
  "status": "pending",
  "message": "認証コードをメールアドレスに送信しました。"
}
```

---

## POST `/api/v1/join/verify`

メールで受信した 6 桁の OTP コードを検証し、認証が成功した場合はサークルの Discord サーバーへの招待リンクを返却します。

* **認可レベル**: `Public`（未認証でアクセス可能）
* **リクエストボディ**:
```json
{
  "join_request_id": "req-uuid-1234-5678",
  "otp_code": "123456"
}
```

### レスポンス (200 OK - 認証成功)
```json
{
  "status": "verified",
  "message": "メール認証が完了しました。以下のリンクからDiscordサーバーに参加してください。",
  "discord_invite_url": "https://discord.gg/xxxxxxxxxx"
}
```

### エラーレスポンス
* `400 Bad Request`: コードが誤っている場合、または試行回数上限（`attempt_count >= 5`）に達した場合。
* `410 Gone`: コードの有効期限（15分）が切れている場合。
