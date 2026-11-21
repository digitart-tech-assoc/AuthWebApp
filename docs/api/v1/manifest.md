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
| `membership_type` | string \| null | `null` | 会員種別のロールなら種別名（`member` / `sub_user` / `obog` / `pre_member` / `admin`）。環境変数のロール ID から決める。GET でだけ返し、保存では使わない |

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
      "is_our_bot": false,
      "membership_type": null
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

### エラーレスポンス
- `400 Bad Request`: 会員種別として成り立たない割当を保存しようとした場合（「会員種別のロールの割当」を参照）
- `403 Forbidden`: Discord で直接付け外しするロールの割当を変更しようとした場合（「Discord で直接付け外しするロール」を参照）
- `500 Internal Server Error`: 割当を保存するときに `DISCORD_TOKEN` が設定されていない場合
- `502 Bad Gateway`: 割当を保存するときに、Discord からロール一覧・Bot のメンバー情報を取得できなかった場合（何も保存しません。`code` は `discord_unavailable`）

`400` / `403` / `502` の `detail` は `{"code": "<種類>", "message": "<説明>"}` の形です（#251）。画面は `code` で文言を出し分けます（`message` は表示しません）。`code` によっては、原因の ID を示す項目が加わります（下の表。#263）。同じステータスを返す認可エラー（admin でない場合の `403` など）の `detail` は文字列のままです。

| `code` | ステータス | 意味 | 追加の項目 |
|---|---|---|---|
| `membership_assignment_invalid` | 400 | 会員種別として成り立たない割当 | `discord_id`（原因のメンバー）、`membership_types`（原因の種別の配列）、`reason`（`partial` / `exclusive`） |
| `protected_role_assignment` | 403 | Discord で直接付け外しするロールの割当の変更 | `role_id`（原因のロール） |
| `discord_unavailable` | 502 | Discord からロールの情報を取得できない | なし |

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
  "role_assignment_changes": {
    "role_id_1": { "added": ["user_id_1"], "removed": ["user_id_2"] }
  }
}
```

### 割当の差分（`role_assignment_changes`、#228）

ロール ID ごとに、追加・削除するメンバーの Discord ID だけを送ります。

| フィールド | 型 | デフォルト | 説明 |
| :--- | :--- | :--- | :--- |
| `added` | string[] | `[]` | 割当を追加するメンバー（すでに割り当て済みなら何もしない） |
| `removed` | string[] | `[]` | 割当を削除するメンバー（割り当てられていなければ何もしない） |

- 送っていないメンバーの割当は変更しません。画面を開いた後に別の経路（self-batch・入会フロー・別の管理者の保存など）で付いた割当は、管理者の保存で外れません。
- `added` / `removed` がどちらも空のロールは何も変更しません（Discord への問い合わせの要否にも含めません）。
- 同じ ID を同じ配列に複数回指定した場合は 1 回分として扱います。
- 同じメンバーを同じロールの `added` と `removed` の両方に指定した場合は `400 Bad Request`（`code` は `assignment_change_conflict`）を返し、何も保存しません。
- 監査ログ（`target_type = 'role_assignment'`）には、実際に追加・削除したメンバーだけを記録します。

> **破壊的変更（#228）:** 以前の `upsert_role_assignments`（ロールごとに変更後の全メンバーを送り、その一覧に置き換える形式）は廃止しました。PATCH のリクエストボディに知らない項目（`upsert_role_assignments` を含む）があると `422 Unprocessable Entity` を返し、何も保存しません。全件の置き換えが必要な場合は `PUT /api/v1/manifest` の `role_assignments` を使います。

### レスポンス (200 OK)
```json
{
  "ok": true
}
```

### エラーレスポンス
- `400 Bad Request`: 会員種別として成り立たない割当を保存しようとした場合（「会員種別のロールの割当」を参照）、または同じメンバーを同じロールの `added` と `removed` の両方に指定した場合（Discord に問い合わせずに返します）
- `403 Forbidden`: Discord で直接付け外しするロールの割当を変更しようとした場合（「Discord で直接付け外しするロール」を参照）
- `422 Unprocessable Entity`: リクエストボディの形式が正しくない場合（廃止した `upsert_role_assignments` などの知らない項目を含む場合も含む）
- `500 Internal Server Error`: 割当を保存するときに `DISCORD_TOKEN` が設定されていない場合
- `502 Bad Gateway`: 割当を保存するときに、Discord からロール一覧・Bot のメンバー情報を取得できなかった場合（何も保存しません。`code` は `discord_unavailable`）

`400` / `403` / `502` の `detail` は `{"code": "<種類>", "message": "<説明>"}` の形です（#251）。画面は `code` で文言を出し分けます（`message` は表示しません）。`code` によっては、原因の ID を示す項目が加わります（下の表。#263）。同じステータスを返す認可エラー（admin でない場合の `403` など）の `detail` は文字列のままです。

| `code` | ステータス | 意味 | 追加の項目 |
|---|---|---|---|
| `membership_assignment_invalid` | 400 | 会員種別として成り立たない割当 | `discord_id`（原因のメンバー）、`membership_types`（原因の種別の配列）、`reason`（`partial` / `exclusive`） |
| `assignment_change_conflict` | 400 | 同じメンバーを同じロールの `added` と `removed` の両方に指定した（#228） | `role_id`（原因のロール）、`discord_id`（原因のメンバー） |
| `protected_role_assignment` | 403 | Discord で直接付け外しするロールの割当の変更 | `role_id`（原因のロール） |
| `discord_unavailable` | 502 | Discord からロールの情報を取得できない | なし |

`assignment_change_conflict` で原因が複数ある場合は、ロール ID・Discord ID の順で最初の 1 件だけを返します。`detail` の例: `{"code": "assignment_change_conflict", "message": "ロール <role_id> で、<Discord ID> を追加と削除の両方に指定しています", "role_id": "<role_id>", "discord_id": "<Discord ID>"}`

---

## 会員種別のロールの割当（PUT / PATCH 共通、#251）

会員種別のロール（環境変数 `MEMBER_ROLE_IDS` / `SUB_USER_ROLE_IDS` / `OBOG_ROLE_IDS` / `PRE_MEMBER_ROLE_ID` で指定したロール）の割当を保存すると、`user_memberships`（会員種別。認可の判定に使う）も同じトランザクションで更新します。

- 割当が実際に変わった人の、変わった種別の行だけを追加・削除します。割当を変えていない人の行は変更しません。
- 新しく追加する行の `assigned_by` は、保存した管理者の Discord ID です。既存の行の `assigned_by` / `assigned_at` は変更しません。
- `admin` の行は保存では変更しません（admin ロールは Discord で直接付け外しし、`POST /api/v1/roles/members/sync` で取り込みます）。
- 変更は監査ログ（`role_audit_logs`、`target_type = 'membership'`）に同じトランザクションで記録します。

次の状態になる保存は `400 Bad Request` を返し、何も保存しません（マニフェストの変更も含めてロールバックします）。判定は、その種別のロールの割当が変わった人だけに行います。

| 条件 | `detail.message` の例 |
|---|---|
| 1 つの種別に複数のロールを設定している場合（例: `MEMBER_ROLE_IDS` に 2 つ）に、その一部だけを持つ状態にする | `"<Discord ID>: 会員種別 'member' のロールは、すべて付けるか、すべて外してください"` |
| `member` と `sub_user`、`pre_member` と `member`、`pre_member` と `sub_user` のロールを同時に持つ状態にする | `"<Discord ID>: 会員種別 'member' と 'sub_user' のロールを同時に付けることはできません"` |

`detail` には、原因の ID を示す項目も入ります（#263）。原因が複数ある場合は、最初に見つかった 1 件だけを返します。

| 項目 | 内容 |
|---|---|
| `discord_id` | 原因のメンバーの Discord ID |
| `membership_types` | 原因の種別の配列（`reason` が `partial` なら 1 件、`exclusive` なら 2 件） |
| `reason` | `partial`（種別のロールの一部だけを持つ状態になる）/ `exclusive`（同時に持てない種別を持つ状態になる） |

`detail` の例: `{"code": "membership_assignment_invalid", "message": "<Discord ID>: 会員種別 'member' と 'sub_user' のロールを同時に付けることはできません", "discord_id": "<Discord ID>", "membership_types": ["member", "sub_user"], "reason": "exclusive"}`

画面は、これらの ID から読み込み済みのメンバー一覧・ロール一覧で名前を引き、Frontend の固定文言に埋めて表示します（一覧にない場合は ID を表示します）。氏名・ユーザー名はレスポンスに含めません（[logging-and-errors.md](../../logging-and-errors.md) §3.2）。

既存のデータで、すでに両方を持っている人については、どちらかを外す保存はできます。

同時に持てない組の判定では、保存で割当が変わる種別は保存後の割当で、変わらない種別は割当または `user_memberships` の行で、その種別を持つかを判断します（行だけあり割当がない人に、同時に持てない種別を付けさせないため）。同じ人の種別を変える保存は、アドバイザリーロックで直列化します。

注意点:
- `SUB_USER_ROLE_IDS` / `OBOG_ROLE_IDS` が未設定の場合、そのロールは一般ロールとして扱い、種別の更新も上の判定も行いません。
- 既存のデータで member と sub垢 の両方の割当を持つ人の sub垢 だけを外すと、member の割当が残ります。この状態で push すると Discord の member ロールが残るため、先に member の割当を外してください（#251 段階 6 より前は、sync で member の行も作られていました）（既存データの整理は `python -m app.scripts.fix_membership_assignments`。[backend.md](../../backend.md) の「保守用スクリプト」）。
- 管理画面は、PATCH で追加・削除したメンバーだけを送ります（#228）。画面を開いたあとに別の経路（入会フロー・`/members/member/add` など）で割当が増えた人は、管理者がそのロールを保存しても外れず、会員種別も失効しません。`PUT` は送った一覧に置き換えるため、送らなかった人の割当は外れます。

---

## Discord で直接付け外しするロール（PUT / PATCH 共通、#251）

Bot が操作できないロール（Bot の最上位ロール以上のロール、managed ロール、`@everyone`）は Discord で直接付け外しします。admin ロールと、Bot に付けるロールが該当します。これらのロールの割当が**実際に変わる**保存は `403 Forbidden` を返し、何も保存しません（マニフェストの変更も含めてロールバックします）。割当が変わらない場合（PUT で送った一覧が保存済みの一覧と同じ場合、PATCH で追加済みのメンバーを `added`・割り当てのないメンバーを `removed` に指定した場合）は拒否しません。

- 判定には、push と同じく Discord のロール一覧と Bot のメンバー情報を使います（`_manageable_role_ids`）。Bot の最上位ロールを特定できない場合は、Discord のすべてのロールを対象にします。
- 割当を含む保存のときだけ Discord に問い合わせます（PUT は `role_assignments` が空、PATCH は `role_assignment_changes` のすべてのロールで `added` / `removed` が空なら問い合わせません）。
- Discord にないロール（仮 ID `draft-…` の新規ロールなど）は対象にしません。

`detail` の例: `{"code": "protected_role_assignment", "message": "ロール <role_id> は Discord で直接付け外しするロールのため、割当を変更できません", "role_id": "<role_id>"}`

`role_id` は原因のロールの ID です（#263）。原因が複数ある場合は、最初に見つかった 1 件だけを返します。
