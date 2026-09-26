# デザインシステム・Tailwind CSS 実装規約

フロントエンドの UI スタイリングにおける公式デザインシステム定義書です。

---

## 1. 原則 (Rules)

### Always
- デザイントークンは Tailwind CSS の標準スケール（4px グリッド・標準サイズ）を使用する。
- ニュートラルカラーは `slate` 系に統一する。
- レスポンシブデザインを意識する。
- クリック・タップ可能な要素（ボタン、リンク、フォーム）は最小 40px（`h-10` または `py-2.5`）の高さを確保する。
- インタラクティブ要素にはフォーカスリング（`focus-visible:ring-2`）を付与する。
- 白背景上のボーダー・テキストは十分なコントラスト比（WCAG AA: 4.5:1 以上）を確保する。

### Never
- 任意値（ブラケット記法 `[...]`）の使用（例外: Discord ブランドカラー `#5865F2` のみ許容）。
- `gray`, `zinc`, `neutral` などの他ニュートラルカラーの混用。
- 白背景での低不透明度ボーダー（`border-slate-900/5` 等）の使用。
- インラインスタイル（`style={{ ... }}`）の使用（例外: 下記「インラインスタイルの例外」を参照）。
- CSS Modules（`*.module.css`）の新規作成・インポート。

### インラインスタイルの例外
実行時にしか値が決まらず、Tailwind のクラスで表現できないものに限り、`style` での指定を許容する。静的な値（`cursor`、`display`、`gap` 等）は必ずクラスにする。

| 用途 | 例 |
| :--- | :--- |
| ドラッグ＆ドロップ（`@dnd-kit`）の位置・遷移 | `style={{ transform: CSS.Transform.toString(transform), transition }}` |
| ユーザー／Discord が指定した色 | `style={{ backgroundColor: role.color }}`（ロールの色ドット、カラースウォッチ） |

---

## 2. デザイントークン (Tokens)

### 2.1 カラーパレット

#### ① サーフェス & ニュートラル
| 用途 | クラス | 備考 |
| :--- | :--- | :--- |
| **全体背景** | `bg-[#f4f5f7]` / `bg-slate-50` | `globals.css` の `--background` に準拠 |
| **カード / モーダル背景** | `bg-white` | 白地 |
| **サブ背景 / テーブル行ホバー** | `bg-slate-50` / `hover:bg-slate-100` | 補助領域 |
| **標準ボーダー** | `border-slate-200` | カード・区切り線（視認性を確保） |
| **入力枠線** | `border-slate-300` / `focus:border-blue-600` | フォームコントロール |

#### ② テキスト階層
| 階層 | クラス | 用途 |
| :--- | :--- | :--- |
| **Primary** | `text-slate-900` | 見出し（h1〜h3）、重要ラベル、主要テキスト |
| **Secondary** | `text-slate-700` | 本文、説明文 |
| **Muted** | `text-slate-500` | メタ情報、補助テキスト |
| **Disabled** | `text-slate-400` | プレースホルダー、非活性テキスト |

#### ③ アクション & ブランド
| 区分 | クラス | 用途 |
| :--- | :--- | :--- |
| **Primary** | `bg-blue-600 hover:bg-blue-700 text-white` | 最重要アクションボタン |
| **CTA Accent** | `bg-gradient-to-r from-blue-600 to-indigo-600 text-white` | アイキャッチCTA |
| **Secondary** | `border border-slate-300 bg-white text-slate-700 hover:bg-slate-50` | キャンセル、サブボタン |
| **Discord** | `bg-[#5865F2] hover:bg-[#4752C4] text-white` | Discord 認証・連携専用 |

#### ④ セマンティック（状態）
| 状態 | テキスト | 背景 | ボーダー |
| :--- | :--- | :--- | :--- |
| **Success** | `text-emerald-700` | `bg-emerald-50` | `border-emerald-200` |
| **Error** | `text-red-700` | `bg-red-50` | `border-red-200` |
| **Warning** | `text-amber-800` | `bg-amber-50` | `border-amber-200` |
| **Info** | `text-sky-800` | `bg-sky-50` | `border-sky-200` |

---

### 2.2 タイポグラフィ

| 要素 | サイズ | ウェイト | 行間 |
| :--- | :--- | :--- | :--- |
| **ページ大見出し (h1)** | `text-2xl sm:text-3xl` | `font-bold` | `tracking-tight` |
| **セクション見出し (h2)** | `text-xl` | `font-bold` | - |
| **カード見出し (h3)** | `text-base` または `text-lg` | `font-semibold` | - |
| **本文 (Body)** | `text-sm` または `text-base` | `font-normal` | `leading-relaxed` |
| **ラベル / ヘッダー** | `text-sm` | `font-medium` / `font-semibold` | - |
| **キャプション / 注記 / バッジ** | `text-xs` | `font-medium` | - |

---

### 2.3 スペーシング & レイアウト

| 項目 | クラス | 適用対象 |
| :--- | :--- | :--- |
| **ページ共通コンテナ** | `mx-auto w-full max-w-5xl px-4 py-8 sm:py-12` | ページの `<main>` タグ（ヘッダー左端と整列） |
| **カード内余白** | `p-6`（小カードは `p-4`） | カードコンテナ |
| **モーダル内余白** | `p-6` | モーダルダイアログ |
| **入力コントロール余白** | `px-3 py-2` | `<input>`, `<select>`, `<textarea>` |
| **ボタン余白** | `px-4 py-2.5` | `<button>`, `<Link>`（h-10 相当） |
| **要素間ギャップ** | `gap-3`（小要素は `gap-1.5` / `gap-2`） | ボタングループ、バッジ列 |

---

### 2.4 角丸 & シャドウ

| 要素 | 角丸 | シャドウ |
| :--- | :--- | :--- |
| **カード / パネル** | `rounded-xl` | `shadow-sm` または `shadow` |
| **モーダル / ダイアログ** | `rounded-2xl` | `shadow-xl` |
| **ボタン / フォーム入力** | `rounded-lg` | - （ボタンホバー時 `shadow-sm`） |
| **バッジ / アバター** | `rounded-full` | - |

---

### 2.5 レスポンシブブレークポイント

- **無印（Mobile）**: 縦積み（`flex-col`）、幅 100%（`w-full`）を基本とする。
- **`sm` (640px)**: ボタングループの横並び（`sm:flex-row sm:w-auto`）。
- **`md` (768px)**: 主要切り替え点。2 カラムグリッド（`md:grid-cols-2`）、サイドバー展開。
- **`lg` (1024px)**: 3 カラムグリッド（`lg:grid-cols-3`）。

---

### 2.6 アニメーション

独自アニメーションは `globals.css` の `@theme` に定義したトークンのみ使用する。コンポーネント側で `@keyframes` を定義しない。

| クラス | 用途 |
| :--- | :--- |
| `animate-fade-in` | モーダル・パネルのオーバーレイ |
| `animate-fade-in-down` | ステータスバナー、選択バー |
| `animate-pop-in` | モーダルダイアログ本体 |
| `animate-slide-in-right` | 右からのスライドインパネル |
| `animate-slide-up` | 画面下部のフローティングバー |

中央寄せは `transform` ではなく flex（`fixed inset-0 flex items-center justify-center`）や `inset-x-0 mx-auto w-fit` で行う。`transform` による中央寄せは、アニメーションの `transform` に上書きされるため。

---

## 3. 共通コンポーネント定義 (Components)

### ボタン (Buttons)
```tsx
// Primary
<button className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
  保存する
</button>

// Secondary
<button className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
  キャンセル
</button>

// Discord
<a href="/auth/discord" className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-[#5865F2] px-5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#4752C4] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5865F2] focus-visible:ring-offset-2">
  Discord でログイン
</a>

// 行内コンパクトボタン（テーブル行・リスト行の中の操作ボタンに限る）
// 見た目は h-8 とし、40px のタップ領域は親の行（min-h-10）と余白で確保する
<button className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50">
  編集
</button>
```

### フォーム入力 (Input)
```tsx
<div className="space-y-1.5">
  <label htmlFor="id" className="block text-sm font-medium text-slate-900">
    ラベル名 <span className="text-red-600">*</span>
  </label>
  <input
    id="id"
    type="text"
    className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-sm transition-colors focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
  />
  <p className="text-xs text-red-600">エラーメッセージ</p>
</div>
```

### カード (Card)
```tsx
<div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
  <h3 className="text-lg font-semibold text-slate-900">タイトル</h3>
  <p className="mt-2 text-sm leading-relaxed text-slate-600">説明文</p>
</div>
```

### バッジ (Badge)
```tsx
// Success
<span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
  承認済み
</span>

// Warning
<span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800">
  確認待ち
</span>
```

### アラート (Alert)
```tsx
<div className="flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
  同期完了: 5 件のロールを更新しました。
</div>
```
