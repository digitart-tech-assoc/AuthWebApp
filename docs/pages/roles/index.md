## 概要

ロール管理ページ（`/roles`）は Discord ロール管理の中核ページです。member/admin/obog ユーザーがロール構成を確認・編集し、Discord サーバーと同期します。member 権限は自分の権限のみ表示、admin/obog 権限はアコーディオン形式で全ロール編集可能です。

## 主要要件

- ロールマニフェスト（構成）の取得・表示
- メンバー権限と管理者権限で異なるUI表示
- ロール同期（バックエンド → Discord）
- ロール Push（マニフェスト更新 → Discord 同期）
- 操作結果（同期成功/失敗）のフィードバック表示

## 非機能要件

- サーバーサイドレンダリング
- ルート保護：middleware と SSR 両方で実装
- セッションベース認可
- Query パラメータで同期結果をフィードバック表示

## 必要項目・操作

### ページに表示される情報
| 項目 | 表示対象 | 説明 |
|-----|---------|------|
| ユーザー名 | 全員 | Discord 表示名・アバター |
| 現在の権限 | 全員 | member/admin/obog など |
| 自分の権限 | member 権限者 | 自分に付与されているロール |
| 全ロール編集 | admin/obog 権限者 | カテゴリ別アコーディオン |

### Query パラメータ（同期結果フィードバック）
| パラメータ | 値 | 意味 |
|-----------|-----|------|
| `synced` | "1" | 同期完了 |
| `roles` | 数字 | 同期されたロール件数 |
| `error` | "1" | 同期エラー |
| `pushed` | "1" | Push 完了 |
| `updated` | 数字 | 更新されたロール数 |
| `created` | 数字 | 新規作成ロール数 |
| `deleted` | 数字 | 削除ロール数 |
| `reordered` | 数字 | 並び替え数 |

### アクセス制御
| ユーザー状態 | 動作 |
|-----------|------|
| 未認証 | `/login?callbackUrl=%2Froles` へリダイレクト |
| 認証済みだが member/admin/obog ではない | `/login?callbackUrl=%2Froles` へリダイレクト |
| 権限を持たない場合 | エラーメッセージ表示 |
| member/admin/obog | ページ表示、権限に応じた編集可能 |

## 操作

1. **ページロード時**
   - 認証チェック（Supabase + バックエンド）
   - ロール権限確認（`app_role`）
   - マニフェスト取得（バックエンド `/api/v1/manifest`）
   - Query パラメータから前回操作結果を解析して表示

2. **Member 権限の場合**
   - 自分のロールのみ表示（`MemberSelfView` コンポーネント）
   - 削除・追加操作可能

3. **Admin/OBOG 権限の場合**
   - 全ロール管理画面表示（`RoleAccordion` コンポーネント）
   - カテゴリ別にアコーディオン展開・折りたたみ
   - ロール追加・削除・並び替え可能

4. **同期操作**
   - 同期ボタン クリック → Query パラメータで結果表示
   - Push ボタン クリック → 変更を Discord へ反映

## 仕様API

### GET /api/v1/manifest
ロールマニフェスト取得

**レスポンス**
```json
{
  "categories": [
    { "id": "string", "name": "string", "color": "hex-color" }
  ],
  "roles": [
    {
      "id": "string",
      "name": "string",
      "category_id": "string",
      "position": number,
      "permissions": ["string"]
    }
  ]
}
```

### GET /api/v1/auth/me
ユーザー権限情報取得

**レスポンス**
```json
{
  "app_role": "member" | "admin" | "obog" | "pre_member" | "none",
  "discord_id": "string",
  "display_name": "string",
  "avatar": "string"
}
```

### POST /api/v1/roles/members/sync
ロール同期実行（バックエンド処理）

**リクエスト**
```json
{
  "action": "sync"
}
```

**レスポンス**
```json
{
  "synced": true,
  "roles_updated": number,
  "errors": []
}
```

## 関連DB

- `roles` テーブル（Discord ロール情報）
- `role_categories` テーブル（ロール分類）
- `user_roles` テーブル（ユーザーへの付与ロール）
- `role_manifest` テーブル（ロール構成マニフェスト）

## 備考

- Member 権限ユーザーは、バックエンドの権限チェックで自分のロールのみ表示するよう制限
- Admin/OBOG 権限で Discord API へのロール操作を実行
- 同期タイムアウト設定あり（推定30秒〜1分）
- アバターは Discord CDN から取得（`https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png`）

## 実装メモ

- `resolveUserInfoFromBackend()` で権限とユーザー情報を取得
- `fetchManifest()` は Server Action で実装
- Query パラメータ解析時に `synced === "1"` という string 比較
- エラーメッセージは赤色パネルで表示（`color: "#b91c1c"`）
- `MemberSelfView` と `RoleAccordion` はコンポーネント分離で権限別UI を実装
