# Digitart 要件定義書・仕様書ガイド (Documentation Guide for AI & Developers)

本ディレクトリ（`docs/`）は、**Digitart サークル認証システム**の公式な要件定義書およびアーキテクチャ仕様書群です。  
人間開発者のみならず、**AI コーディングエージェント（Antigravity, GitHub Copilot, Cursor 等）がタスク着手時に仕様・責務・データ構造を正確に把握するための公式ドキュメント（一次情報）** として体系化されています。

---

## 1. ドキュメント体系とディレクトリ構成

```text
docs/
├─ README.md              # 【本ファイル】仕様書の全体構成・AI 向け探索ガイド
├─ frontend.md            # フロントエンド（Next.js 16）基盤要件・共通アーキテクチャ
├─ backend.md             # バックエンド（FastAPI）基盤要件・主要責務・環境変数
├─ discord-bot.md         # Discord Bot（discord.py）基盤要件・差分同期ロジック
├─ db.md                  # データベーススキーマ仕様（全テーブル・VIEW・リレーション）
├─ api/                   # REST API 詳細仕様
│  ├─ README.md           # API 全体一覧（全34エンドポイント）・共通認証仕様
│  └─ v1/                 # FastAPI ルーター（リソース）単位の詳細仕様
│     ├─ auth.md          # ログイン・登録・セッション・ユーザー情報
│     ├─ contact.md       # お問い合わせ送信
│     ├─ dev.md           # 開発環境用ロール切替
│     ├─ discord.md       # ギルド情報・メンバー検索
│     ├─ join.md          # 仮入会（青学生 / 入学見込み）・OTP認証
│     ├─ manifest.md      # ロールマニフェスト取得・一括更新
│     ├─ members.md       # 会員一覧・部費照合・Bot連携用内部API
│     ├─ roles.md         # ロール付与・剥奪・権限変更・Discord Push
│     ├─ student.md       # 青学生認証・本入会アンケート・学生プロフィール
│     └─ sync.md          # Discord Bot への同期トリガー
├─ pages/                 # フロントエンド画面別要件定義
│  ├─ README.md           # 画面サイトマップ・ルーティング一覧
│  ├─ index.md            # ルート（/）
│  ├─ login/              # ログイン画面（/login）
│  ├─ contact/            # お問い合わせ（/contact）
│  ├─ non-member/         # 対象外案内（/non-member）
│  ├─ profile/            # プロフィール編集（/profile）
│  ├─ roles/              # ロール管理（/roles: 一般表示・管理者表示）
│  ├─ members/            # 会員管理（/members）
│  └─ join/               # 入会申請（/join, /join/form, /join/member）
└─ manuals/               # 運用者・ユーザー向け操作マニュアル
   ├─ admin_manual.md     # 管理者向け運用マニュアル
   ├─ manual.md           # 一般ユーザー向けマニュアル
   └─ user_manual.md      # 入会希望者・新入生向けマニュアル
```

---

## 2. AI エージェント向け逆引き探索ガイド

タスクの目的に応じて、以下のドキュメントを優先して参照してください。

| 実装・改修したい内容 | 最初に読むべき仕様書 | 関連して確認する仕様書 |
| :--- | :--- | :--- |
| **画面 UI・ページ機能の変更** | [pages/README.md](./pages/README.md) および各画面仕様書 | [frontend.md](./frontend.md), [frontend/README.md](../frontend/README.md) |
| **API の追加・変更・確認** | [api/README.md](./api/README.md) | [api/v1/*.md](./api/v1/), [backend.md](./backend.md) |
| **DB カラム・テーブルの変更** | [db.md](./db.md) | `backend/app/db/schema.py`, `backend/alembic/` |
| **認証・認可・ロール（RBAC）** | [backend.md](./backend.md) | [api/v1/auth.md](./api/v1/auth.md), [db.md](./db.md) |
| **入会・仮入会・学生認証フロー** | [pages/join/README.md](./pages/README.md) | [api/v1/join.md](./api/v1/join.md), [api/v1/student.md](./api/v1/student.md) |
| **Discord ロール同期・Bot 連携** | [discord-bot.md](./discord-bot.md) | [api/v1/sync.md](./api/v1/sync.md), [api/v1/members.md](./api/v1/members.md) |
| **環境変数の追加・仕様確認** | [`.env.example`](../.env.example) | [backend.md](./backend.md), [frontend.md](./frontend.md) |

---

## 3. システムアーキテクチャの基本原則

仕様書および実装を追従するにあたり、以下の設計原則を遵守してください：

1. **Backend 単一集約原則**:
   - データベース（PostgreSQL）への直接アクセスおよびビジネスロジックはすべて `backend/` (FastAPI) に集約されます。
   - フロントエンドおよび Discord Bot は、すべて FastAPI の REST API（`/api/v1` または `/internal`）を介してデータを読み書きします。
2. **動的 RBAC 認可**:
   - ユーザーの権限（`admin`, `member`, `obog`, `pre_member`, `none`）は、PostgreSQL の `v_users_with_app_role` VIEW に基づいて動的に判定されます。
3. **Frontend の Colocation パターン**:
   - Next.js 16 (App Router) では、特定ルート固有のコンポーネントは各ルート配下の `_components/` に配置します。
4. **一次情報優先・架空仕様の排除**:
   - 仕様を記述・改修する際は、必ず一次情報（実装コード、Alembic マイグレーションファイル、公式ドキュメント）を確認してください。
   - 実装されていない架空のテーブルや推測の機能を仕様書に混在させてはなりません。

---

## 4. 仕様書の更新規約

コードを変更した際は、対応するドキュメントも同一 PR 内で更新してください：

- **API を追加・変更した場合**:
  - `docs/api/README.md` のエンドポイント一覧表を更新。
  - 対応する `docs/api/v1/<resource>.md` にリクエスト／レスポンス JSON 仕様を追記・修正。
- **DB マイグレーションを追加した場合**:
  - `docs/db.md` に新テーブル・変更カラム・インデックスを反映。
- **画面やルーティングを追加・変更した場合**:
  - `docs/pages/README.md` のサイトマップを更新。
  - `docs/pages/<route>/index.md` に画面仕様・操作要件を記述。
- **環境変数を追加した場合**:
  - [`.env.example`](../.env.example) を更新し、対応する `docs/frontend.md`, `docs/backend.md`, `docs/discord-bot.md` に反映。
