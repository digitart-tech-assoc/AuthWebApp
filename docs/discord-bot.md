# Discord Bot 要件定義・アーキテクチャ (discord.py)

## 1. 概要
discord.py (Python 3.11+) をベースに、FastAPI による内部受信用 HTTP サーバーを並列稼働（Hypercorn / asyncio）させる Bot サービスです。
バックエンド（FastAPI）からの指示を受け、Discord サーバー内のロール差分同期（Reconciliation）や通知を実行します。

---

## 2. 主要機能・責務

1. **同期指示の受付 (`POST /internal/sync`)**:
   - バックエンドからの内部同期要求を `Authorization: Bearer <SHARED_SECRET>` で認証。
   - バックグラウンドでロール差分同期タスク（`run_reconcile`）をキック。
2. **ヘルスチェック (`GET /internal/health`)**:
   - コンテナオーケストレーション（Kubernetes / Docker）用の稼働確認エンドポイント。
3. **ロール差分同期 (Reconciliation)**:
   - バックエンドの内部エンドポイント（`GET /api/v1/members/internal/lists`）から最新のメンバーおよび仮入会者リストを取得。
   - Discord REST API（`/guilds/{guild_id}/members/{user_id}/roles/{role_id}`）を用いて、`PRE_MEMBER_ROLE_ID` および `MEMBER_ROLE_IDS` の付与・剥奪を最小限の呼び出しで実行。
   - 処理結果（成功・失敗件数、エラー理由）を JSON レスポンスとして返却・ログ出力。
4. **制約・例外処理**:
   - Bot 自身の最上位ロールより上位のロールは Discord の仕様上操作不可。
   - レート制限（HTTP 429）や Discord API エラー時は適切にハンドリングし、サマリーにエラー詳細を記録。

---

## 3. 必要な環境変数（Discord Bot）

環境変数は [`.env.example`](../.env.example) に準拠します：

| 環境変数 | 必須 | 説明 |
| :--- | :---: | :--- |
| `DISCORD_TOKEN` | ○ | Discord Bot トークン |
| `DISCORD_GUILD_ID` | ○ | 対象 Discord サーバー（ギルド）の ID |
| `BACKEND_URL` | ○ | バックエンド API の URL（例: `http://backend:8000`） |
| `SHARED_SECRET` | ○ | 内部サービス間通信用シークレット |
| `PRE_MEMBER_ROLE_ID` | ○ | 仮入会者ロールの Discord ロール ID |
| `MEMBER_ROLE_IDS` | ○ | 正式メンバーロールの Discord ロール ID（カンマ区切りで複数指定可） |

---

## 4. 運用・検証要件
- Pod は Kubernetes 上で `ReplicaSet: 1`（二重起動による多重同期防止）。
- livenessProbe / readinessProbe に `GET /internal/health` を設定。
- 構文・コンパイル検証: `python -m compileall app/`

