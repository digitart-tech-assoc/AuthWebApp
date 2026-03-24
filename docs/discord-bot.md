# Discord Bot 要件定義 (discord.py)

## 概要
discord.py を用い、Bot 本体はイベントループ内で受信用 HTTP サーバーを並列稼働させる（FastAPI または aiohttp）。FastAPI が DB と API の一元管理を行い、Bot は Backend からの指示で Discord と同期する責務を持つ。

## 主要機能
- 指示受付: Backend からの同期命令を受ける内部エンドポイント（認証: SHARED_SECRET）。
- 同期 (Reconciliation) ロジック:
  1. Backend API から「あるべき状態」を取得。
  2. Discord の現状（guild.roles）を取得。
  3. 差分を算出（作成・更新・削除・順序変更）。
  4. 最小限の API コールで反映し、結果を Backend に返却／ログ記録。
- 例外/制約処理: Bot 自身のロールより上位のロールは操作不可。権限不足・API レート制限はリトライと audit_logs 記録。

## 非機能要件
- Pod は k8s 上で `ReplicaSet: 1`（二重起動による重複動作防止）。
- livenessProbe / readinessProbe を設定し、イベントループ停止時に再起動されること。
- 同期はバッチ化してレートリミットを避ける。

## セキュリティ
- 受信用エンドポイントは `Authorization: Bearer <SHARED_SECRET>` を検証する。

## 開発・運用
- ローカルは docker-compose で Bot と Backend を同時起動して連携テストを行う。
- エラー発生時は `events` テーブルや `audit_logs` に詳細を残す。
