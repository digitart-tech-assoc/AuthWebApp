# マニフェスト API 仕様 (`/api/v1/manifest`)

本ドキュメントは、宣言型ロールマニフェスト（カテゴリ・ロール・メンバー割当）の取得、一括保存、差分保存に関する API 仕様です。

---

## データモデル定義

### Category（カテゴリ）
| フィールド | 型 | デフォルト | 説明 |
| :--- | :--- | :--- | :--- |
| `id` | string | - | カテゴリID（UUID等） |
| `name` | string | - | カテゴリ名（例: "学年", "役職"） |
| `display_order` | integer | `0` | 画面上の並び順 |
| `is_collapsed` | boolean | `false` | 初期状態で折りたたむか |
| `permissions` | integer | `0` | カテゴリ単位の権限ビットフラグ |
| `is_restricted` | boolean | `false` | 管理者のみ編集可能な保護カテゴリか |

### Role（ロール）
| フィールド | 型 | デフォルト | 説明 |
| :--- | :--- | :--- | :--- |
| `role_id` | string | - | Discord ロールID（Snowflake） |
| `name` | string | - | ロール名 |
| `color` | string | `"#000000"` | ロールカラー（HEXカラーコード） |
| `hoist` | boolean | `false` | メンバー一覧で別枠表示するか |
| `mentionable` | boolean | `false` | メンション可能か |
| `permissions` | integer | `0` | Discord 権限ビットフラグ |
| `position` | integer | - | Discord 内のロール階層位置 |
| `category_id` | string \| null | `null` | 所属するカテゴリID |
| `is_our_bot` | boolean | `false` | アプリケーション用 Bot 自身のロールか |

---

## GET `/api/v1/manifest`

DB に保存されている宣言型ロールマニフェスト（全カテゴリ、全ロール、メンバー割当）を取得します。

* **認可レベル**: `Member`（`member`, `sub_user`, `obog`, `admin`）
* **リクエストヘッダー**:
  ```http
  Authorization: Bearer <SUPABASE_JWT_TOKEN>
  ```
* **リクエストボディ**: なし

### レスポンス (200 OK)
```json
{
  "categories": [
    {
      "id": "cat_1",
      "name": "役職",
      "display_order": 0,
      "is_collapsed": false,
      "permissions": 0,
      "is_restricted": true
    }
  ],
  "roles": [
    {
      "role_id": "123456789012345678",
      "name": "代表",
      "color": "#FFD700",
      "hoist": true,
      "mentionable": true,
      "permissions": 8,
      "position": 50,
      "category_id": "cat_1",
      "is_our_bot": false
    }
  ],
  "role_assignments": {
    "123456789012345678": ["discord_user_id_1", "discord_user_id_2"]
  }
}
```

---

## PUT `/api/v1/manifest`

マニフェストを一括置換保存します。

* **認可レベル**: `Admin`（管理者のみ）
* **リクエストヘッダー**:
  ```http
  Authorization: Bearer <SUPABASE_JWT_TOKEN>
  ```
* **リクエストボディ**:
```json
{
  "categories": [ ... ],
  "roles": [ ... ],
  "role_assignments": {
    "role_id_1": ["user_id_1"]
  }
}
```

### レスポンス (200 OK)
保存された `Manifest` オブジェクトが返却されます。

---

## PATCH `/api/v1/manifest`

マニフェストの差分のみを保存します（パフォーマンス最適化・ドラッグ＆ドロップ用）。

* **認可レベル**: `Admin`（管理者のみ）
* **リクエストヘッダー**:
  ```http
  Authorization: Bearer <SUPABASE_JWT_TOKEN>
  ```
* **リクエストボディ**:
```json
{
  "upsert_categories": [
    {
      "id": "cat_new",
      "name": "新カテゴリ",
      "display_order": 1,
      "is_collapsed": false,
      "permissions": 0,
      "is_restricted": false
    }
  ],
  "delete_category_ids": ["cat_old"],
  "upsert_roles": [
    {
      "role_id": "role_id_1",
      "name": "更新後ロール名",
      "color": "#00FF00",
      "hoist": false,
      "mentionable": false,
      "permissions": 0,
      "position": 10,
      "category_id": "cat_new",
      "is_our_bot": false
    }
  ],
  "delete_role_ids": [],
  "upsert_role_assignments": {
    "role_id_1": ["user_id_1", "user_id_2"]
  }
}
```

### レスポンス (200 OK)
```json
{
  "ok": true
}
```
