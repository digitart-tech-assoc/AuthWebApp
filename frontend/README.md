# AuthWebApp Frontend

Next.js App Router (React 19 / TypeScript) を採用した、Discord 認証・ロール管理および会員登録システムです。

---

## 1. クイックスタート

### 前提条件
- Node.js 20.x 以上
- npm 10.x 以上

### 開発環境のセットアップ

```bash
# 依存パッケージのインストール
cd frontend
npm install

# 開発サーバーの起動 (Turbopack)
npm run dev
```

ブラウザで [http://localhost:3000](http://localhost:3000) を開いて動作を確認します。

### 検証・動作確認コマンド

```bash
# TypeScript 型チェック（コミット前に必須）
npx tsc --noEmit

# 本番ビルド検証（コミット前に必須）
npm run build

# Docker環境での統合動作確認（ルートディレクトリで実行）
docker compose up --build
```

---

## 2. ディレクトリ構造と責務

フロントエンドのコードは `src/` 配下に関心ごと・レイヤーごとに整理されています。

```text
frontend/src/
├── actions/             # Server Actions（"use server"）
│   └── studentRegistration.ts  # 学生情報登録・OTP送信等のサーバー処理
├── app/                 # Next.js App Router（ルーティング & Colocation）
│   ├── layout.tsx       # 全体レイアウト（ヘッダー・ナビゲーション）
│   ├── page.tsx         # トップページ
│   ├── roles/           # ロール管理画面（/roles）
│   │   ├── page.tsx
│   │   └── _components/ # 【Colocation】ロール管理専用コンポーネント・Hooks
│   │       ├── RoleAccordion.tsx       # ロール一覧・アコーディオン
│   │       ├── SortableCategoryItem.tsx # カテゴリ個別行（DnD対応）
│   │       ├── RoleDiffModal.tsx       # 差分確認モーダル
│   │       ├── useRoleModals.ts        # モーダル状態管理カスタムフック
│   │       ├── useCategoryDnd.ts       # 並び替えDnDカスタムフック
│   │       └── roleDiff.ts             # 差分検知・ペイロード構築純粋関数
│   ├── join/            # 入会・参加申請フロー（/join）
│   │   ├── page.tsx
│   │   ├── _components/ # 【Colocation】join専用ステップ・モーダルコンポーネント
│   │   │   ├── FormStep1Eligibility.tsx
│   │   │   ├── FormStep2Input.tsx
│   │   │   ├── FormStep3Survey.tsx
│   │   │   ├── FormStep4OTP.tsx
│   │   │   ├── FormStep5Complete.tsx
│   │   │   └── OTPModal.tsx
│   │   └── form/        # フォームルーティング
│   ├── profile/         # プロフィール編集画面（/profile）
│   │   ├── page.tsx
│   │   └── _components/ # 【Colocation】profile専用コンポーネント
│   │       └── ProfileForm.tsx
│   └── api/             # Route Handlers（Next.js バックエンドプロキシAPI）
├── components/          # 複数画面で使い回す共通UIパーツ（共通ライブラリ）
│   ├── forms/           # 汎用フォームパーツ（StudentProfileForm, NameInput等）
│   └── OTPInput.tsx     # 汎用OTP入力フィールド
├── lib/                 # ユーティリティ・APIクライアント・基盤ロジック
│   ├── api/             # クライアント向けAPI通信関数
│   │   └── roles.ts     # ロール・マニフェスト関連通信（fetch関数群）
│   ├── backendFetch.ts  # FastAPI バックエンド通信ヘルパー
│   └── supabase.ts      # Supabase クライアント
└── types/               # 【重要】共通ドメイン型定義（一元管理）
    ├── roles.ts         # Role, Category, Manifest, Member, Payload 型
    └── join.ts          # SurveyAnswers, StudentProfile, CheckResult 型
```

---

## 3. フロントエンド開発ルール（コーディング規約）

新しく参加したエンジニアや React 初心者の方が、迷わず安全にコードを書くための基本原則です。

### ① ファイル命名規則
| 種別 | 命名規則 | 例 |
| :--- | :--- | :--- |
| **React コンポーネント** | `PascalCase.tsx` | `RoleAccordion.tsx`, `FormStep1Eligibility.tsx` |
| **カスタムフック** | `use + CamelCase.ts` | `useRoleModals.ts`, `useCategoryDnd.ts` |
| **ロジック・ユーティリティ・API** | `camelCase.ts` | `roleDiff.ts`, `studentRegistration.ts` |
| **CSS Modules** | `コンポーネント名.module.css` | `StudentProfileForm.module.css` |

### ② 型定義の集約（`src/types/` の利用）
- 複数のコンポーネントやアクションにまたがるドメイン型（`Role`, `Category`, `Member`, `StudentProfile` など）は、**必ず `src/types/` 配下のファイルで定義**してください。
- コンポーネントファイル（`.tsx`）内で定義した型を外部からインポートし合う循環依存は禁止です。
- **Next.js Turbopack の制約**: `"use server"`（Server Actions）ファイルから `export type` を行うと、ビルド時にモジュール解決エラーが発生します。型は必ず純粋な `.ts` ファイル（`src/types/`）からエクスポートしてください。

### ③ コンポーネント分割と単一責任の原則
- **1ファイル 300〜500 行以内** を目安とし、1,000行を超える巨大コンポーネント（神コンポーネント）を作らないでください。
- コンポーネントが肥大化したら、以下の役割に分離します：
  1. **UIパーツ**: 見た目とPropsの受け渡しに専念するサブコンポーネント（例: `SortableCategoryItem.tsx`）
  2. **カスタムフック**: `useState` / `useCallback` などの状態管理（例: `useRoleModals.ts`）
  3. **純粋関数**: 外部状態に依存しない計算・差分ロジック（例: `roleDiff.ts`）
- 特定ページでのみ使われるコンポーネントは、`app/<page>/_components/` 配下に配置（Colocation）してカプセル化します。

### ④ スタイリング指針
- プロジェクト全体で**Tailwind CSS**を使用します。CSS Modulesは使用しません。
- 詳細なデザイントークンや実装規約は [docs/frontend/styling-guide.md](../docs/frontend/styling-guide.md) を、CSS Modules からの移行手順・PRチェックリストは [docs/frontend/css-migration-plan.md](../docs/frontend/css-migration-plan.md) を参照してください。
- **レイヤー逆転の禁止**: `components/`（共通パーツ）から `app/`（個別ページ）のモジュールやCSSをインポートする逆流依存は厳禁です。共通コンポーネントは Tailwind CSS または専用スタイルで自己完結させてください。

### ⑤ 通信層（APIクライアント）の集約
- コンポーネントの中に `fetch("/api/...")` を直接ベタ書きしないでください。
- API 呼び出しは `src/lib/api/`（例: `src/lib/api/roles.ts`）に関数としてまとめ、リクエストとレスポンスの型を明示してください。

### ⑥ コミット・変更プロトコル
- **コミット粒度は小さく**: 1つの改修で1つの関心事（1フックの抽出、1型の移動など）単位でコミットします。
- **改変前後のセーフティチェック**:
  - 改変前: 影響範囲を把握し、リスクを評価する。
  - 改変後: 必ず `npx tsc --noEmit` と `npm run build` を実行してエラーが 0 件であることを確認してからコミットする。

---

## 4. 主な技術スタック

- **フレームワーク**: Next.js 16 (App Router / Turbopack)
- **UIライブラリ**: React 19
- **言語**: TypeScript
- **DnD（ドラッグ＆ドロップ）**: `@dnd-kit/core`, `@dnd-kit/sortable`
- **アイコン**: `lucide-react`
- **認証**: Supabase Auth (Discord OAuth2)
- **スタイリング**: CSS Modules / Tailwind CSS
