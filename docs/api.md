# API 仕様（主要エンドポイント）

このファイルは Frontend と Bot が利用する FastAPI の公開 API と内部 API（Bot 通信用）を簡潔にまとめた一覧です。

## 認証
- フロントエンド: Discord OAuth2 によるセッション管理を前提。
- サービス間（Frontend <-> Backend, Backend <-> Bot）: `Authorization: Bearer <SHARED_SECRET>` を利用する。

実装状況（2026-03-24）:
- Frontend は Keycloak（Auth.js）セッションを使い、Backend API へ access token を転送する。
- Backend は Keycloak JWT を検証する（issuer / jwks / audience）。
- 段階移行のため、Backend 公開 API は一時的に `SHARED_SECRET` も受け入れる。

## エンドポイント

### GET /api/v1/manifest
- 説明: DB にある "あるべき状態"（カテゴリとロール）を取得する。
- レスポンス 200:

```json
{
  "categories": [{ "id": "cat_1", "name": "学年", "display_order": 0, "is_collapsed": false }],
  "roles": [{ "role_id": "123..", "name": "2024年", "color": "#00FF00", "hoist": false, "mentionable": false, "permissions": 0, "position": 10, "category_id": "cat_1" }]
}
```

### PUT /api/v1/manifest
- 説明: UI の編集結果を一括保存する。保存成功後は Bot に同期要求を行う（内部的には `/internal/notify-bot` などを呼ぶ）。
- リクエスト例:

```json
{ "categories": [...], "roles": [...] }
```

- レスポンス 200:
```json
{ "ok": true }
```

### POST /api/v1/sync
- 説明: 明示的に同期をトリガーする。ヘッダーに `Authorization: Bearer <SHARED_SECRET>` を必要とする。
- ボディ: `{"action":"sync_roles"}` のような簡潔な JSON を受け付ける。

### 認証設定用の環境変数（Backend）
- `KEYCLOAK_ISSUER_URL`
- `KEYCLOAK_AUDIENCE`
- `KEYCLOAK_JWKS_URL`（省略時は issuer から自動解決）
- `SHARED_SECRET`（移行期フォールバックと内部 API 用）

### GET /api/v1/events
- 説明: Bot がポーリングで未処理イベントを取得するために使える（アウトボックスパターン）。

### POST /internal/notify-bot
- 説明: Backend が Bot の内部受信用エンドポイントに向けて通知するためのラッパー（内部用途）。
- 認証: `SHARED_SECRET`。

## エラーハンドリング
- 標準は HTTP ステータスコードと JSON `{ "error": "message" }` を返す。
- Bot との連携で失敗した場合は 502 を返し、監査ログに記録する。

## 開発時の注意点
- Frontend は直接 DB に触らない。すべて Backend 経由。
- Bot も DB を直接触らず、Backend API から必要な状態を取得する設計が推奨される。
