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
   - PostgreSQL (Supabase) への全クエリ・トランザクション処理を一元管理。
   - Alembic によるマイグレーション管理。
   - DB アクセスは同期処理（psycopg2）のため、`async def` のエンドポイントから呼ぶときは `await asyncio.to_thread(func, *args)` で別スレッドに逃がし、イベントループを止めない。bcrypt によるハッシュ化・照合も同様に扱う。
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
| `DB_POOL_SIZE` | - | クライアント側コネクションプールで常時保持する接続数（デフォルト: `5`） |
| `DB_POOL_MAX_OVERFLOW` | - | `DB_POOL_SIZE` を超えて一時的に作成できる接続数（デフォルト: `5`） |
| `DB_POOL_TIMEOUT` | - | プール枯渇時に接続の返却を待つ秒数。超過するとエラー（デフォルト: `10`） |
| `DB_POOL_RECYCLE` | - | 接続を再作成するまでの経過秒数。Pooler 側のアイドル切断対策（デフォルト: `300`） |
| `SHARED_SECRET` | ○ | 内部サービス間通信用シークレット。16文字以上。`FASTAPI_ENV=production` で未設定または16文字未満の場合は起動しない（それ以外の環境では警告のみ） |
| `SUPABASE_JWT_SECRET` | ○ | Supabase JWT 署名検証シークレット（HS256用） |
| `NEXT_PUBLIC_SUPABASE_URL` | ○ | Supabase プロジェクト URL（JWKS 公開鍵取得用） |
| `DISCORD_TOKEN` | ○ | Discord Bot トークン（メンバー取得・ロール操作用） |
| `DISCORD_GUILD_ID` | ○ | 対象 Discord サーバー（ギルド）の ID |
| `ADMIN_ROLE_IDS` | ○ | admin ロールの Discord ロール ID（カンマ区切りで複数指定可）。会員種別はロール名ではなく ID で判定する |
| `MEMBER_ROLE_IDS` | ○ | member ロールの Discord ロール ID（カンマ区切りで複数指定可） |
| `PRE_MEMBER_ROLE_ID` | ○ | pre-member ロールの Discord ロール ID |
| `OBOG_ROLE_IDS` | - | OBOG ロールの Discord ロール ID（カンマ区切りで複数指定可）。未設定の場合、`/members/sync` で obog の差分を計算しない |
| `SUB_USER_ROLE_IDS` | - | sub垢 ロールの Discord ロール ID（カンマ区切りで複数指定可）。未設定の場合、`/members/sync` で sub_user の差分を計算しない |
| `BOT_INTERNAL_URL` | - | Discord Bot サーバーの内部 URL（`http://host:8000` でも、`/internal/sync` までを含む URL でもよい。デフォルト: `http://discord-bot:8000`）。旧名の `DISCORD_BOT_URL` は、`BOT_INTERNAL_URL` が未設定のときだけ読む |
| `BREVO_API_KEY` | ○ | Brevo メール送信 API キー |
| `BREVO_SENDER_EMAIL` | ○ | 送信元メールアドレス |
| `BREVO_SENDER_NAME` | ○ | 送信元表示名 |
| `CONTACT_CHANNEL_ID` | - | お問い合わせ通知先 Discord チャンネル ID |
| `FASTAPI_ENV` | - | 稼働環境（`production`, `development`, `local` 等）。`production` では `ADMIN_ROLE_IDS` / `MEMBER_ROLE_IDS` / `PRE_MEMBER_ROLE_ID` が未設定だと起動しない（それ以外の環境では警告のみ） |

---

## 4. 開発・検証コマンド
- サーバー起動: `uvicorn app.main:app --host 0.0.0.0 --port 5174 --reload`
- テスト実行: `pytest`
- DB マイグレーション適用: `alembic upgrade head`
  - **本番では、Backend をデプロイする前に適用してください。** 例えば `0007_add_role_audit_logs` を適用せずに新しい Backend を動かすと、`role_audit_logs` への記録が失敗するため、マニフェストの保存やロールの割り当ての更新がすべて失敗します。
- マイグレーション作成: `alembic revision -m "<message>"`
- 動作確認: `docker compose up --build` で Docker 環境を立ち上げて実施

## 5. 保守用スクリプト

### 会員種別とロールの割当の整理（`app.scripts.fix_membership_assignments`、#251）
`user_memberships`（会員種別）と `role_member_assignments`（ロールの割当）の既存データの食い違いを整理します。内容は `app/db/membership_backfill.py` を参照してください。

- sub垢 と member の両方を持つ人: member ロールの割当を外します。sub_user の行もある場合は member の行も消します。
- 行はあるが割当がない人（member / sub_user / obog / pre_member）: その種別のロールの割当を補完します。ただし次の場合は補完せず、件数だけを表示します。
  - 補完すると、同時に持てない組（member と sub垢、pre-member と member / sub垢）になる場合（`skipped_conflicting_rows`）。例: OTP 検証済みでプロフィール未送信の、pre_member の行と member の割当を持つ人
  - sub垢 の割当があり、sub_user の行がなく member の行だけがある人（`member_rows_of_sub_role_holders`）。先に sync で揃えてください
- 割当はあるが行がない人: 変更せず、件数だけを表示します（`assignments_without_row`）。
- admin の行と admin ロールの割当は扱いません。
- 任意の種別（`SUB_USER_ROLE_IDS` / `OBOG_ROLE_IDS`）が未設定だと、その種別は整理しません。出力の `unconfigured_role_id_env_vars` で確認してください。

```bash
# Backend のコンテナ内で実行する（DATABASE_URL と会員種別のロール ID の環境変数が必要）
python -m app.scripts.fix_membership_assignments           # 件数の確認だけ（dry-run。何も書き込まない）
python -m app.scripts.fix_membership_assignments --apply   # 反映する（監査ログに operation = 'membership_backfill' で記録する）
```

- 出力は件数だけで、Discord ID は出しません。`--apply` では、記録した監査ログの `request_id` も出します。
- 両テーブルのロックを 5 秒待っても取れない場合は、何も変更せずに失敗します。時間をおいて再実行してください。

#### 推奨する手順
> **#251 段階 6 以降の注意:** sync は member / sub_user / obog / pre_member の行を書き込まなくなりました。下の手順 2・6 と、`member_rows_of_sub_role_holders` の「先に sync で揃えてください」は、段階 6 より前の手順です。段階 6 以降に件数が 0 でない場合は、管理画面の割当の保存で揃えてください。

**#173 の修正（push 後の Bot の reconcile が届くようになる）より前に行ってください。** 行はあるが割当がない人は、reconcile が届くと push のたびにロールを外して付け直すことになります。

1. sub垢 ロールの Discord の権限を確認する（手順 5 の push で、sub垢 と member の両方を持つ人の member ロールが外れるため）。
2. 管理画面の「Discord同期」（`POST /api/v1/roles/members/sync`）を実行し、sub垢 を持つ人の行を sub_user に揃える。
3. dry-run で件数を確認する。`skipped_conflicting_rows` / `member_rows_of_sub_role_holders` / `assignments_without_row` が 0 でない場合は、個別に確認する。
4. `--apply` で反映する。
5. 管理画面から push する（補完した割当が Discord に付き、外した member ロールが外れる）。429 で途中で止まった場合は、もう一度 push する。
6. 必要なら、もう一度 sync する。
