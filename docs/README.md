# 要件定義書・仕様書インデックス (docs/)

本ディレクトリは、Digitart サークル認証システムの公式仕様書群です。  
AI コーディングエージェントおよび開発者は、タスクの対象領域に応じて以下のドキュメントを参照・同期してください。

---

## 1. ドキュメントマップ

| 開発領域 / タスク | 参照先ドキュメント | 主な内容 |
| :--- | :--- | :--- |
| **API 仕様** | [api/README.md](./api/README.md) | 全34エンドポイント一覧・リソース別仕様（`api/v1/*.md`）への案内 |
| **画面・UI 要件** | [pages/README.md](./pages/README.md) | 画面サイトマップ・各画面個別要件（`pages/**/index.md`）への案内 |
| **DB スキーマ** | [db.md](./db.md) | 全テーブル・VIEW（`v_users_with_app_role`等）・ENUM 定義 |
| **Frontend 基盤** | [frontend.md](./frontend.md) | Next.js 16 構成・Colocation規約・画面一覧・環境変数 |
| **UI スタイリング規約** | [frontend/styling-guide.md](./frontend/styling-guide.md) | デザインシステム定義書・Tailwind CSS 実装規約 |
| **CSS 移行計画** | [frontend/css-migration-plan.md](./frontend/css-migration-plan.md) | CSS Modules からの移行手順・置換対応表・PRチェックリスト |
| **Backend 基盤** | [backend.md](./backend.md) | FastAPI アーキテクチャ・動的RBAC・主要責務・環境変数 |
| **Discord Bot** | [discord-bot.md](./discord-bot.md) | discord.py ロール差分同期ロジック・内部API・環境変数 |
| **運用マニュアル** | [manuals/](./manuals/) | 管理者・一般ユーザー・入会希望者向け操作手順 |

---

## 2. 仕様書の更新規約

コードを変更した際は、対応するドキュメントも同一 PR 内で必ず更新してください：

- **API の追加・変更**: [api/README.md](./api/README.md) の一覧および対応する [api/v1/<resource>.md](./api/v1/) の JSON 仕様を更新。
- **DB スキーマの変更**: [db.md](./db.md) のテーブル・VIEW 定義を更新。
- **画面・ルーティングの変更**: [pages/README.md](./pages/README.md) のサイトマップおよび該当 `pages/**/index.md` を更新。
- **環境変数の追加・変更**: [`.env.example`](../.env.example) を更新し、対応する `frontend.md` / `backend.md` / `discord-bot.md` に反映。
