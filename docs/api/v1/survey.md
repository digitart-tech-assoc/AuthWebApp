# 入会アンケート API 仕様 (`/api/v1/survey`)

本ドキュメントは、本入会手続き時に回答されるサークルの認知経路・活動動機・興味分野に関するアンケート保存 API の仕様です。

---

## POST `/api/v1/survey/`

本入会フォーム（Step 3）で回答されたアンケートデータを `member_survey_responses` テーブルへ保存します。

* **認可レベル**: `Authenticated`（Discord 連携済みユーザー）
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "digitart_channels": ["Twitter (X)", "新歓ビラ", "友人からの紹介"],
  "digitart_channels_other": null,
  "circle_search_channels": ["青学サークルまとめサイト", "Instagram"],
  "circle_search_other": null,
  "discord_invite_source": "新歓公式LINE",
  "discord_invite_other": null,
  "interested_fields": ["Web開発", "AI・機械学習", "インフラ・クラウド"],
  "interested_fields_other": "ゲーム開発にも興味があります",
  "motivations": ["プログラミングスキルを身につけたい", "仲間を作りたい"],
  "motivations_other": null,
  "join_request_id": "req-uuid-1234"
}
```

### レスポンス (200 OK)
```json
{
  "id": 42,
  "created_at": "2026-03-28T12:05:00Z"
}
```
