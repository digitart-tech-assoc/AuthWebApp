# Frontend 要件定義・開発ガイド

## 1. 概要
Next.js 16 (App Router / React 19 / TypeScript / Tailwind CSS) を採用した、サークルメンバーおよび入会希望者向けの Web フロントエンドです。
UI とユーザー操作に専念し、すべてのデータ永続化・認可処理はバックエンド（FastAPI）および Route Handlers / Server Actions 経由で行います。

> [!TIP]
> **開発ガイド・コーディング規約**:
> 詳細なディレクトリ構造、Colocation パターン（`_components/`）、型定義ルールは [frontend/README.md](../frontend/README.md) を参照してください。
> デザインシステム・スタイリング規約は [frontend/styling-guide.md](./frontend/styling-guide.md)、CSS Modules 移行計画は [frontend/css-migration-plan.md](./frontend/css-migration-plan.md) を参照してください。
> 各画面の個別仕様は [docs/pages/README.md](./pages/README.md) を参照してください。

---

## 2. 主要機能・画面要件

フロントエンドは以下の主要機能を提供します：

1. **認証・アカウント連携（`/login`, `/auth/callback`）**:
   - Supabase Auth を利用した Discord OAuth2 サインイン／サインアウト。
   - ログイン後、バックエンド（`/api/v1/auth/login-or-register`）へユーザー情報を同期し、権限に応じた画面へ誘導。
2. **入会申請フロー（`/join`）**:
   - **在学生仮入会（`/join/form/aoyama-student`）**: 学生番号入力から大学メールを自動補完。
   - **入学見込み仮入会（`/join/form/prospective-student`）**: メール認証（OTP）を経て Discord 招待リンクを案内。
   - **本入会（`/join/member`）**: 5 ステップ形式（適格性判定 → 基本情報入力 → アンケート回答 → 大学メールOTP認証 → 完了）。
3. **ロール管理（`/roles`）**:
   - **一般メンバー**: 自身の所属ロール確認、セルフロールの付与・解除。
   - **管理者（Admin）**: カテゴリ・ロールのドラッグ＆ドロップ並び替え（`@dnd-kit`）、プロパティ編集、マニフェスト差分保存（PATCH）、Discord への反映（Push）。
4. **会員管理（`/members` - 管理者限定）**:
   - 仮入会者一覧の閲覧、部費（入会費）支払い状態の確認・照合承認、正式メンバー追加。
5. **プロフィール管理（`/profile`）**:
   - メンバーの学生情報（学生番号、氏名、学部等）の確認・更新。
6. **お問い合わせ（`/contact`）**:
   - 運営宛て問い合わせフォーム（Discord チャンネル通知）。
7. **開発者ツール（`DevRoleSwitcher`）**:
   - ローカル/プレビュー環境でのお手軽ロール切替モーダル（本番環境では自動非表示）。

---

## 3. 非機能要件・アーキテクチャ
- **Colocation パターン**: 各ルート固有のコンポーネントは `app/<route>/_components/` 配下に配置する。
- **UI スタイリング**: Tailwind CSS を基本とし、インラインスタイルや任意値（`[...]`）の使用を避ける。詳細は [Tailwind CSS スタイリング実装規約](./frontend/styling-guide.md) を参照。
- **パフォーマンス**: 大量ロール表示時もストレスのない操作感（必要に応じて仮想化）。
- **セキュリティ**:
  - API キーやシークレットをクライアントサイドに露出しない。
  - バックエンド通信時は Supabase セッション JWT を `Authorization: Bearer <TOKEN>` で安全に転送。

---

## 4. 必要な環境変数（Frontend）

環境変数は [`.env.example`](../.env.example) に準拠します：

| 環境変数 | 必須 | 説明 | 例 |
| :--- | :---: | :--- | :--- |
| `NEXT_PUBLIC_SUPABASE_URL` | ○ | Supabase プロジェクトの URL | `https://xxxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ○ | Supabase 匿名公開キー (Anon Key) | `eyJhbGciOi...` |
| `NEXT_PUBLIC_SUPABASE_REDIRECT_URL` | ○ | OAuth 認証コールバック URL | `http://127.0.0.1:5173/auth/callback` |
| `NEXT_PUBLIC_BACKEND_URL` | ○ | クライアント側（ブラウザ）から呼ぶバックエンド URL | `http://localhost:5174` |
| `NEXT_PUBLIC_SITE_URL` | ○ | フロントエンドの公開ルート URL | `http://127.0.0.1:5173` |
| `BACKEND_URL` | ○ | サーバーサイド（Route Handlers / SSR）から呼ぶバックエンド URL | `http://backend:5174` |
| `AUTH_REQUIRED` | - | 認証強制フラグ（デフォルト: `true`） | `true` / `false` |

---

## 5. 開発・検証コマンド
- 開発サーバー起動: `npm run dev`（ポート: 5173）
- 型チェック: `npx tsc --noEmit`
- Lint 検証: `npm run lint`
- ビルド確認: `npm run build`
- 動作確認: `docker compose up --build` で Docker 環境を立ち上げて実施

