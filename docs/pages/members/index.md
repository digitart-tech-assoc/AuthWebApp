## 概要

メンバー管理ページ（`/members`）は、仮入会者（Pre-Member）の一覧表示と入会費清算管理ページです。Discord ID で検索可能で、管理者が仮入会者の入会費支払いを追跡・記録します。本ページは admin 権限推定で、入会処理に関連したデータ管理を行います。

## 主要要件

- 仮入会者（Pre-Member）リストの表示
- Discord ID による検索
- 入会費支払い状態の管理
- 入会費清算記録機能
- モーダルダイアログで詳細操作

## 非機能要件

- クライアントコンポーネント（React フック使用）
- 非同期データフェッチ（useEffect / useCallback）
- リアルタイム検索フィード
- ローディング・エラーハンドリング

## 必要項目・操作

### Pre-Member 表示情報
| 項目 | 型 | 説明 |
|-----|-----|------|
| Discord ユーザー名 | string | Discord の username |
| Discord 表示名 | string | Discord の display_name（異なる場合は別表示） |
| Discord ID | string | 一意識別子 |
| Supabase ID | string | 認証システムのユーザーID |
| User ID | string | バックエンド内部ID |
| 登録日 | timestamp | 仮入会した日時 |
| 支払い状態 | boolean | `is_paid` フラグ |

### 操作ボタン
| ボタン | 条件 | 動作 |
|--------|------|------|
| 詳細 | `is_paid === false` | モーダル開く |
| 支払済み | `is_paid === true` | 無効化（表示のみ） |

## 操作

1. **ページロード時**
   - 全 Pre-Member リスト取得
   - ローディング表示中

2. **検索実行**
   - Discord ID 入力 → 検索ボタン クリック
   - `getPreMemberList(query)` 実行
   - 検索結果表示

3. **クリアボタン クリック**
   - 検索入力をリセット
   - 全リスト再取得

4. **詳細ボタン クリック（支払い未済のメンバー）**
   - モーダルダイアログ表示
   - メンバー情報を表示
   - メモ入力フィールド表示

5. **入会費清算ボタン クリック**
   - メモを送信
   - `registerPaidInvitation()` 実行
   - 成功メッセージ表示 → 1秒後モーダル自動閉じ
   - リスト再読み込み

6. **キャンセルボタン クリック**
   - モーダルを閉じる
   - 入力状態もリセット

## 仕様API

### Server Action: getPreMemberList
**ファイル**: `/frontend/src/actions/members.ts`

```typescript
async function getPreMemberList(query?: string): Promise<PreMember[]>
```

**パラメータ**
- `query`（オプション）: Discord ID で絞り込み

**レスポンス**
```typescript
interface PreMember {
  discord_id: string;
  discord_username: string;
  discord_display_name?: string;
  supabase_user_id?: string;
  user_id?: string;
  assigned_at?: string; // ISO 8601 datetime
  is_paid: boolean;
}
```

### Server Action: registerPaidInvitation
**ファイル**: `/frontend/src/actions/members.ts`

```typescript
async function registerPaidInvitation(
  discord_id: string,
  note?: string
): Promise<{ ok: boolean }>
```

**パラメータ**
- `discord_id`: 対象メンバーのDiscord ID
- `note`（オプション）: 清算に関するメモ（例：「銀行振込済み」）

**レスポンス**
```json
{ "ok": true | false }
```

## 関連DB

- `pre_members` テーブル（仮入会者情報）
- `paid_invitations` テーブル（入会費清算記録）

## 備考

- 本ページは admin 権限推定（アクセス制御は middleware で実施）
- 支払い済みメンバーの詳細ボタンは無効化（グレーアウト）
- 検索クエリが空の場合は全リスト表示
- モーダルのメモ入力は入会費の支払い方法などを記録するためのフリーテキスト

## 実装メモ

- `useState` で members, loading, error, selectedMember, noteInput などを管理
- `useCallback` で `loadMembers` 関数をメモ化（依存関係管理）
- `useEffect` で マウント時に自動的に `loadMembers()` 呼び出し
- エラーメッセージは赤色パネル表示（`bg-red-100 border border-red-400 text-red-700`）
- 成功メッセージは緑色パネル表示（`bg-green-100 border border-green-400 text-green-700`）
- Modal は `fixed inset-0 bg-black/50` でオーバーレイ実装
