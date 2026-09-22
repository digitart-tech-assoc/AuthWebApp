# CSS Modules 移行計画書 (Issue #93)

CSS Modules（`*.module.css`）から Tailwind CSS への移行手順およびレビュー規約です。

---

## 1. 目的と基本方針

- **一本化**: フロントエンド全体のスタイリングを Tailwind CSS に統一し、CSS Modules を全廃する。
- **標準トークン準拠**: 旧 CSS の数値を機械的に任意値（`text-[26px]`, `rounded-[14px]` 等）で移植せず、必ず [styling-guide.md](./styling-guide.md) の標準トークンに寄せる。
- **影響局所化**: 画面・コンポーネント単位で PR を分割し、1 PR = 1 つの論理的変更とする。

---

## 2. 移行手順

1. **対象スタイルの確認**:
   - 対象コンポーネント（`app/**` または `components/**`）と対応する `*.module.css` を特定する。
2. **Tailwind トークンへの置換**:
   - クラス指定を [styling-guide.md](./styling-guide.md) の標準トークンに置き換える。
   - インラインスタイル（`style={{ ... }}`）が残っている場合は Tailwind クラスに変換する。
3. **不要ファイルの削除**:
   - 参照されなくなった `*.module.css` を削除する。
4. **検証の実行**:
   - `cd frontend` 配下で以下を実行し、すべてエラー 0 件であることを確認する：
     - 型チェック: `npx tsc --noEmit`
     - Lint: `npm run lint`
     - ビルド: `npm run build`
5. **表示・操作確認**:
   - デスクトップ表示およびモバイル表示（幅 375px〜414px）で崩れがないことを確認する。

---

## 3. 旧 CSS 値と Tailwind トークンの対応表

旧 CSS のプロパティを移植する際は、以下の標準トークンを使用してください。

| プロパティ | 旧 CSS 値（px） | 任意値（禁止） | Tailwind 推奨トークン |
| :--- | :--- | :--- | :--- |
| **フォントサイズ** | 26px | `text-[26px]` | `text-2xl` (24px) または `text-3xl` (30px) |
| | 15px | `text-[15px]` | `text-sm` (14px) または `text-base` (16px) |
| | 13px | `text-[13px]` | `text-sm` (14px) |
| | 11px | `text-[11px]` | `text-xs` (12px) |
| **行間** | 1.7 | `leading-[1.7]` | `leading-relaxed` |
| **角丸** | 14px | `rounded-[14px]` | `rounded-xl` (12px) |
| | 10px / 6px | `rounded-[10px]` / `rounded-[6px]` | `rounded-lg` (8px) または `rounded-md` (6px) |
| **余白 (Padding/Margin)** | 18px / 20px | `p-[18px]` / `px-[18px]` | `p-4` (16px) または `p-5` (20px) |
| | 14px | `p-[14px]` | `p-3.5` (14px) または `p-4` (16px) |
| | 6px | `my-[6px]` | `my-1.5` (6px) または `my-2` (8px) |
| | 72px | `pb-[72px]` | `pb-16` (64px) または `pb-20` (80px) |
| **枠線色** | rgba(15,23,42,0.04) | `border-slate-900/5` | `border-slate-200` |
| **テキスト色** | #6b7280 (Gray) | `text-gray-500` | `text-slate-500` |
| | #0f172a (Dark) | - | `text-slate-900` |
| **シャドウ** | 0 6px 18px rgba(...) | `shadow-[0_6px_18px_...]` | `shadow-sm` または `shadow` |

---

## 4. PR レビューチェックリスト

PR 作成時およびレビュー時は以下を確認してください。

- [ ] 任意値指定（`[...]`）が含まれていないか（Discord カラー `#5865F2` 等の例外を除く）。
- [ ] カラーが `slate` 系に統一されているか（`gray` や `zinc` の混入がないか）。
- [ ] 白背景上のボーダーや文字のコントラストが担保されているか（`border-slate-200` 等）。
- [ ] モバイル幅（375px〜414px）で横スクロールやレイアウト崩れが発生していないか。
- [ ] ボタンやリンクのタップ領域が最低 40px 以上確保されているか。
- [ ] 不要になった `*.module.css` が漏れなく削除されているか。
- [ ] `tsc`、`lint`、`build` がすべてパスしているか。
