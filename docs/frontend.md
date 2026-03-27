# Frontend 要件定義

## 概要
Next.js 15 (App Router) を採用する。フロントは UI と「宣言（Desired State）」の編集に専念し、データの読み書きはすべて FastAPI 経由で行う。

## 主要要件
- 認証: Discord OAuth2 によるサインイン。
- 表示: `role_categories` ごとにロールをグルーピングし、アコーディオンで展開/収納する（shadcn/ui 推奨）。
- 編集: ドラッグ&ドロップでロールの並び替え・カテゴリ移動（@dnd-kit/core 推奨）。
- プロパティ操作: ロール名、カラー、hoist、mentionable、permissions の編集。
- 同期: 保存後に FastAPI の API を呼び出して Bot に同期（`POST /api/v1/sync`）を依頼。

## 非機能要件
- 大量ロールでも操作が滑らか（必要に応じ仮想化を導入）。
- Server Actions を活用して機密情報をクライアントに露出しない実装。
- アクセシビリティ: キーボード操作での並べ替えを提供する。

## API（FastAPI 経由）
- `GET /api/v1/manifest` — DB 上のマニフェスト（カテゴリ+ロール）を取得。
- `PUT /api/v1/manifest` — UI 側の一括更新（並び/カテゴリ変更等）。
- `POST /api/v1/sync` — 同期トリガー（FastAPI が Bot に指示を送る）。

## 開発・運用
- ローカルは docker-compose で起動（frontend:3000）。
- UI コンポーネントは再利用可能に設計、README に使用方法を記載する。

## 実装メモ（2026-03-24）
- Frontend は Supabase Auth を用いてサインインを処理します。
- 保護対象ページ（現状: `/roles`）は未ログイン時に `/api/auth/signin` へリダイレクトします。
- Backend への API 呼び出しは、Supabase のセッション／JWT を用いて認可します。

## 必要な環境変数（Frontend）
- `AUTH_SECRET`
- `AUTH_REQUIRED` (`true` / `false`)
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `BACKEND_URL`

## トラブルシュート
- 症状: `/api/auth/signin?callbackUrl=%2Froles` が 500 を返す。
- 主因: 認証プロバイダの設定値不足または `NEXT_PUBLIC_SUPABASE_*` が未設定。
- 対処:
	1. `NEXT_PUBLIC_SUPABASE_URL` と `NEXT_PUBLIC_SUPABASE_ANON_KEY` を確認する。
	2. `AUTH_REQUIRED=true` を使う場合は、バックエンド側で Supabase JWT の検証設定が有効であることを確認する。
