# Digitart サークル認証システム

## Build & Test
コミット前に、変更したディレクトリの検証をすべて実行し、パスすることを確認する。

- Frontend（`cd frontend`）: 型チェック `npx tsc --noEmit`、Lint `npm run lint`、ビルド `npm run build`
- Backend（`cd backend`）: `pytest`
- Discord Bot（`cd discord-bot`）: `python -m compileall app/`

## Architecture
- `frontend/`: Next.js (App Router / TypeScript / Tailwind CSS)。各ルートの `_components/` に置く Colocation パターンを守る。
- `backend/`: FastAPI / SQLAlchemy。DB アクセスとビジネスロジックを集約し、Bot への指示（同期）も Backend 経由で発行する。
- `discord-bot/`: discord.py。サーバー内ロールの同期・通知を担う。
- API を変更するときは、呼び出し側（frontend / discord-bot）の型・実装・テストを同じ PR 内で更新する。
- 要件定義書: `docs/`

## Boundaries

### Always
- 応答・コメント・ドキュメント・コミットメッセージ・PR は日本語で書く。
- 仕様や挙動を述べる前に、一次情報（実装コード / 要件定義書 / 公式ドキュメント）を確認する。
- 確認できていないことは断定しない。仕様は「推定」、実行できなかった検証は「未実施」と明記する。
- 要件定義書・実装コード・ユーザー指示の間で矛盾がある場合は、独断せずユーザーに確認する。
- 依頼範囲外の変更を混ぜない。無関係な問題を見つけたら、修正せず報告する。
- ブランチ名: `<ユーザー名>/<種別>-<内容>`（例: `chrom/fix-xxx`）
- コミット: `feat:` `fix:` `refactor:` `docs:` `test:` `add:` `delete:` のいずれかを先頭に付け、1コミット = 1つの論理的変更とする。
- PR: [`.github/pull_request_template.md`](.github/pull_request_template.md) を使う。
- バグ修正・機能追加では、対応するテストを追加・更新する。
- 環境変数の仕様は `.env.example` で確認し、追加・変更時は同ファイルも更新する。

### Ask first
- 公開 API エンドポイントや DB スキーマの破壊的変更。
- 新規の外部パッケージ（npm / pip）の追加。
- 共通基盤・認証ロジック・CI/CD ワークフローの権限設定の変更。
- 破壊的操作（削除処理、外部サービスへの書き込み等）の実行。

### Never
- `.env` や `authwebapp-secret.yaml` の読み取り、および API キー・トークン・パスワードなどのハードコード。
- メンバーの個人情報（Discord ID 等）をログ・テストデータ・コミットに含めること。
- 作業ブランチ以外（特に `main`）への直接 push / merge、`force push`、`--no-verify` による hook 回避。
- テストを通すためだけの、テストの削除・スキップ・弱体化。
- デバッグ用の仮コードやログのコミット。