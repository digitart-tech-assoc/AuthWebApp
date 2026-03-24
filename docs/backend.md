# Backend 要件定義 (FastAPI)

## 概要
FastAPI を唯一の DB アクセス層として集約する。Frontend はすべての読み書きをこの Backend 経由で行い、Bot への指示（同期トリガー）も Backend が発行する。

## 主要責務
- DB 操作の集中管理: PostgreSQL (k8s 上) への全クエリを担う。
- 認証/認可: Discord OAuth2 によるユーザー検証、サーバー内の Administrator 権限判定。
- Bot ブリッジ: Frontend からの同期要求を受け、Bot の受信用エンドポイントへ HTTP POST で指示を送る。
- 監査ログ: 変更操作を `audit_logs` に保存。

## 推奨 API（抜粋）
- `GET /api/v1/manifest` — マニフェスト取得。
- `PUT /api/v1/manifest` — マニフェスト一括保存。
- `POST /api/v1/sync` — Bot に同期命令を発行。
- `POST /internal/bot/notify` — (認証付き) Bot 指示用エンドポイント呼び出しのラッパー。

## 認証・セキュリティ
- Frontend / Bot 間は `Authorization: Bearer <SHARED_SECRET>` を必須とする（K8s Secret で管理）。
- Discord トークン等の機密は K8s Secret / environment で注入。

## DB スキーマ（要旨）
- role_categories: id, name, display_order, is_collapsed
- role_manifests: role_id, name, color, hoist, mentionable, permissions (BigInt), position, category_id, is_managed_by_app
- events: id, event_type, payload, status(pending|claimed|processed|failed), claimed_by, retry_count
- audit_logs: id, action, actor_id, target_id, target_type, details, created_at

## 運用要件
- ローカル開発は docker-compose を想定。CI/CD では k8s マニフェストを用いる。
- DB マイグレーションは Flyway や Alembic 等で管理。
