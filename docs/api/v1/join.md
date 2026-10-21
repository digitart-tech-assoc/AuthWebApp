# 入会申請・仮入会 OTP 認証 API 仕様 (`/api/v1/join`)

本ドキュメントは、入学見込み生等の仮入会申請、ワンタイムパスワード（OTP）送信、および認証コード検証に関する API 仕様です。

---

## POST `/api/v1/join/request`

仮入会申請を受け付け、指定されたメールアドレス宛に 6 桁のワンタイムパスワード（OTP）を送信します。

* **認可レベル**: `Public`（未認証でアクセス可能）
* **制限事項**: `form_type == "prospective-student"` の場合、受付期間（毎年2月1日～4月5日）外は `403 Forbidden` を返します。
* **レート制限**: クライアント IP ごとに 5 回 / 10 分。大学のネットワーク（`133.2.0.0/16`）からは 50 回 / 10 分（[README](../README.md#レート制限)）。
* **リクエストボディ**:
```json
{
  "email": "prospective@example.com",
  "confirm_email": "prospective@example.com",
  "name": "青山 太郎",
  "form_type": "prospective-student",
  "metadata": {
    "year": 2026
  }
}
```

* `metadata`: `join_requests` に専用カラムがないフォーム固有の項目を入れ、`join_requests.metadata`（JSONB）に保存する。省略時は `{}`。
  * `prospective-student`: `year`（入学予定年度、整数）。**必須**。
  * `aoyama-student`: `student_id`（学生番号）

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

### エラーレスポンス
* `400 Bad Request`: 次のいずれかの場合。`detail` に理由が入る。
  * `email` と `confirm_email` が一致しない（`"Emails do not match"`）。
  * `form_type == "prospective-student"` で `metadata.year` が整数でない、または存在しない（`"metadata.year is required for prospective-student"`）。
* `403 Forbidden`: `form_type == "prospective-student"` で受付期間外の場合。
* `409 Conflict`: 同じメールアドレスで処理中・完了済みの申請がある場合（`"Email already registered"`）。
* `429 Too Many Requests`: レート制限の上限に達した場合（`"Too many requests. Please try again later."`）。申請の作成・メール送信は行わない。`Retry-After` ヘッダーに待ち秒数が入る。
* `500 Internal Server Error`: OTP メールの送信に失敗した場合（`"Failed to send OTP email"`）、またはその他の処理に失敗した場合（`"Internal server error"`）。

エラーレスポンスの `detail` には固定文言のみを返し、例外メッセージやメール送信 API の応答本文は含めません（詳細は Backend のログに出します。[logging-and-errors.md](../../logging-and-errors.md)）。

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
* `400 Bad Request`: 次のいずれかの場合。`detail` は `"Invalid or expired OTP code"`。
  * コードが誤っている。試行回数（`attempt_count`）を 1 増やす。
  * コードの有効期限（15分）が切れている。
  * 未検証の OTP が存在しない。
* `409 Conflict`: 同じ OTP の検証が同時に行われており、行ロック（`SELECT ... FOR UPDATE`）の待ち時間が上限（`OTP_LOCK_TIMEOUT_MS` = 3 秒）を超えた場合。試行回数は消費しない。`detail` は `"同じ認証コードの確認が同時に行われています。しばらく待ってから再度お試しください。"`。
* `429 Too Many Requests`: 試行回数上限（`attempt_count >= 5`）に達している場合（`"Maximum OTP attempts exceeded"`）。5 回目の誤入力の時点でコードは失効する。
