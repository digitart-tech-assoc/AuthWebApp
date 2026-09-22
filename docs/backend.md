# Backend 要件定義・アーキテクチャ (FastAPI)

## 1. 概要
FastAPI (Python 3.11+) を採用した、本システムのコアビジネスロジックおよびデータベースアクセス層を集約するバックエンドサーバーです。
フロントエンド（Next.js）および Discord Bot は、すべてこのバックエンドが提供する REST API（`/api/v1`）を介して安全にデータ操作・同期を行います。

> [!TIP]
> **API 仕様書・DB スキーマ**:
> - API エンドポイント詳細仕様: [docs/api/README.md](./api/README.md)
> - データベーススキーマ仕様: [docs/db.md](./db.md)

---

## 2. 主要責務

1. **データベース操作の集中管理**:
   - PostgreSQL (Supabase / local) への全クエリ・トランザクション処理を一元管理。
   - Alembic によるマイグレーション管理。
2. **認証・動的 RBAC 認可**:
   - Supabase Auth の JWT（RS256 / ES256 / HS256）を署名検証。
   - `v_users_with_app_role` ビューによるロール（`admin`, `member`, `obog`, `pre_member`, `none`）の動的判定。
   - 内部連携用 `SHARED_SECRET` によるベアラートークン認証。
3. **入会・認証ロジック**:
   - ワンタイムパスワード（OTP）の生成、bcrypt ハッシュ化、試行回数制限（最大5回）、有効期限管理。
   - 青山学院大学の学生メールアドレス自動導出および在学生所有権の検証。
   - Brevo（メール配信 API）による OTP 送信。
4. **Discord Bot・外部サービス連携**:
   - Discord Bot 受信用エンドポイント（`POST /internal/sync`）への同期要求発行。
   - Discord API 直接呼び出し（ギルドメンバー情報・ロール一覧の取得、チャンネルへの Embed 通知）。
   - 期限切れ仮入会ロールの自動クリーンアップ（`pre_member_removal_log`）。
5. **開発環境用サポート**:
   - ローカル検証用ロール切替 API（`FASTAPI_ENV` ホワイトリスト判定により、本番環境では自動遮断）。

---

## 3. 必要な環境変数（Backend）

環境変数は [`.env.example`](../.env.example) に準拠します：

| 環境変数 | 必須 | 説明 |
| :--- | :---: | :--- |
| `DATABASE_URL` | ○ | PostgreSQL 接続文字列（Supabase Pooler / Transaction mode） |
| `SHARED_SECRET` | ○ | 内部サービス間通信用シークレット |
| `SUPABASE_JWT_SECRET` | ○ | Supabase JWT 署名検証シークレット（HS256用） |
| `NEXT_PUBLIC_SUPABASE_URL` | ○ | Supabase プロジェクト URL（JWKS 公開鍵取得用） |
| `DISCORD_TOKEN` | ○ | Discord Bot トークン（メンバー取得・ロール操作用） |
| `DISCORD_GUILD_ID` | ○ | 対象 Discord サーバー（ギルド）の ID |
| `DISCORD_BOT_URL` | - | Discord Bot サーバーの内部 URL（デフォルト: `http://discord-bot:8000`） |
| `BREVO_API_KEY` | ○ | Brevo メール送信 API キー |
| `BREVO_SENDER_EMAIL` | ○ | 送信元メールアドレス |
| `BREVO_SENDER_NAME` | ○ | 送信元表示名 |
| `CONTACT_CHANNEL_ID` | - | お問い合わせ通知先 Discord チャンネル ID |
| `FASTAPI_ENV` | - | 稼働環境（`production`, `development`, `local` 等） |

---

## 4. 開発・検証コマンド
- サーバー起動: `uvicorn app.main:app --host 0.0.0.0 --port 5174 --reload`
- テスト実行: `pytest`
- DB マイグレーション適用: `alembic upgrade head`
- マイグレーション作成: `alembic revision -m "<message>"`
- 動作確認: `docker compose up --build` で Docker 環境を立ち上げて実施


