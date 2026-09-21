# お問い合わせ API 仕様 (`/api/v1/contact`)

本ドキュメントは、サークル外・サークル内からの問い合わせフォーム受付、および運営用 Discord チャンネルへの通知に関する API 仕様です。

---

## POST `/api/v1/contact/submit`

問い合わせフォームの内容を受け付け、運営の Discord サーバー（環境変数 `CONTACT_CHANNEL_ID`）に Embed メッセージとして即時通知します。

* **認可レベル**: `Public`（未認証でアクセス可能）
* **リクエストボディ**:
```json
{
  "name": "質問 太郎",
  "email": "question@example.com",
  "affiliation": "他大学 / 一般",
  "subject": "サークル見学について",
  "message": "次回の活動日を見学させていただくことは可能でしょうか？"
}
```

### レスポンス (200 OK)
```json
{
  "status": "success",
  "message": "お問い合わせを送信しました",
  "message_id": "123456789012345678"
}
```

### エラーレスポンス
* `500 Internal Server Error`: Discord Bot のトークン未設定、またはチャンネル送信失敗時。
