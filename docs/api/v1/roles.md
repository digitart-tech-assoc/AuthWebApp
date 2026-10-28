# ロール操作 API 仕様 (`/api/v1/roles`)

本ドキュメントは、Discord ロールの取得、Discord への同期（Push）、セルフロール付与・解除・作成、権限変更に関する API 仕様です。

ロール定義とロール割り当ては DB（`role_manifests` / `role_member_assignments`）を Desired State とし、Discord への反映は Push で行います。Discord の状態を DB に取り込み直す API はありません（Discord 側で直接変更した内容は、次回の Push で DB の状態に戻ります）。

---

## POST `/api/v1/roles/push`

DB のマニフェスト（`role_manifests`）を Desired State として読み、Discord サーバーのロールへ適用（作成・更新・削除・並び順調整）します。続けて、DB のロール割り当て（`role_member_assignments`）と Discord 上のメンバーのロールの差分を反映し、最後に Discord Bot へ reconcile（同期）を依頼します。

* **認可レベル**: `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**: なし（DB のマニフェストを読むため、ロール定義は送りません）

### レスポンス (200 OK)
```json
{
  "ok": true,
  "guild_id": "1488327535132413974",
  "updated": 2,
  "created": 1,
  "deleted": 0,
  "reordered": 1,
  "skipped_managed": 1,
  "assigned_adds": 3,
  "assigned_removes": 1,
  "skipped_members": 0,
  "bot_reconciled": true,
  "errors": []
}
```

| 項目 | 説明 |
|---|---|
| `ok` | `errors` が空のとき `true` |
| `guild_id` | 対象のギルド ID |
| `updated` | 定義を更新したロールの数（変更がないロールは数えない） |
| `created` | Discord に新しく作成したロールの数 |
| `deleted` | マニフェストにないため Discord から削除したロールの数（managed ロールと `@everyone` は削除しない） |
| `reordered` | 並び順が変わったロールの数。push 前の Discord の並び順と比べ、ほかのロールとの相対的な順序が変わったロールを数える（1 件を別の位置へ移動した場合は、ほかのロールの `position` の値が変わっても `1`）。今回作成したロールは `created` で数えるため含めない。並び替えのリクエストは変更の有無にかかわらず毎回送る。並び替えに失敗した場合は `0` |
| `skipped_managed` | managed ロールまたは `@everyone` のため更新しなかったロールの数 |
| `assigned_adds` | メンバーに付与したロールの延べ数 |
| `assigned_removes` | メンバーから解除したロールの延べ数 |
| `skipped_members` | ギルド外のため割り当て反映をスキップしたユーザー数。割り当てはDBに保持し、削除しない |
| `bot_reconciled` | Discord Bot への reconcile の依頼が成功したか |
| `errors` | 失敗した操作の内容（文字列の配列）。対象の ID・件数・HTTP ステータス（ステータスがない場合は例外の型名）のみを含み、例外メッセージや Discord の応答本文は含めない（詳細は Backend のログに出す） |

### エラーレスポンス
* 一部の操作（ロールの作成・更新・削除・並び替え、メンバーへの割り当て）が失敗しても、処理は続けて HTTP 200 を返します。この場合 `ok` は `false` になり、`errors` に失敗内容が入ります。
* `500 Internal Server Error`: `DISCORD_TOKEN` が設定されていない場合。
* `502 Bad Gateway`: 処理の開始時に Discord からロール一覧を取得できなかった場合（`"Failed to fetch roles from Discord"`）。この場合、Discord には何も反映しません。

### Discord への反映方式
* **メンバーのロール割り当て**: DB の割り当てと Discord 上の現在のロールの差分をメンバーごとにまとめて反映します。
  * 各メンバーへの反映の直前に、そのメンバーの DB の割り当てを読み直して差分を計算し直します。push の途中で self-batch などにより変わった割り当てを、開始時の DB の情報で巻き戻さないためです。読み直したあと反映するまでの短い間に割り当てが変わった場合は、巻き戻ることがあります。
  * 差分が 1 件だけのメンバーは、ほかのロールに触れない `PUT` / `DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id}` で反映します。
  * 差分が 2 件以上のメンバーは、直前に `GET /guilds/{guild_id}/members/{user_id}` で現在のロールを取り直して差分を計算し直し、1 回の `PATCH /guilds/{guild_id}/members/{user_id}` で反映します。push の途中で付与・解除されたロールを、開始時の情報で上書きしないためです。
  * 設定後のロール一覧は Discord 上の現在のロールを元に組み立てるため、managed ロールなど差分の対象外のロールは外れません。
  * managed ロール、Bot メンバーが持つ最上位ロール以上の位置にあるロール、push で削除したロールは差分の対象外です。判定にはBot統合ロールではなく、Botメンバーが実際に持つロールを使います。Botメンバーまたは基準ロールを特定できない場合は、誤操作を防ぐため全ロールの割り当てをスキップします。並び替え後のロール一覧の取得に失敗した場合は、push 開始時のロール一覧で判定します。
  * 対象メンバーがサーバーにいない（404）場合はスキップし、`errors` には含めません。
  * Discordから取得したギルドメンバーに含まれない割り当てはDiscord APIへ送信せず、`skipped_members` に人数を返します。DBの割り当ては自動削除しません。
  * 権限不足（403）の場合は、そのメンバーの差分がすべて反映されないため `errors` に記録します（Discord ID は含めません）。
  * その他の失敗は、そのメンバーの Discord ID・差分の件数・HTTP ステータス（ステータスがない場合は例外の型名）を `errors` に記録し、次のメンバーへ進みます（例: `"Failed to update roles for 123456789012345678 (+1/-0): DiscordAPIError HTTP 500"`）。
* **レート制限（429）**: Discord から `429 Too Many Requests` を受けた場合は、レスポンスの `retry_after`（なければ `Retry-After` ヘッダー）の秒数だけ待って再試行します。再試行は最大 3 回、1 回の待ち時間は最大 10 秒です（`backend/app/core/config.py` の `DISCORD_RATE_LIMIT_MAX_RETRIES` / `DISCORD_RATE_LIMIT_MAX_WAIT`）。上限を超えた場合は失敗として `errors` に記録します。
  * メンバーのロール割り当ての反映中に上限を超えた場合は、続けて送っても 429 を重ねるだけで、Discord の無効リクエスト数の上限（超えると IP 単位で一時的に遮断される）に近づくため、残りのメンバーへの反映を打ち切ります。`errors` には反映できなかった残りの人数を記録します（Discord ID は含めません）。時間をおいて push をやり直してください。
  * 429 を受ける前でも、応答の `X-RateLimit-Remaining` が 0 であれば `X-RateLimit-Reset-After` の秒数（最大 10 秒）だけ待ってから次のリクエストを送ります。
  * 429 の警告ログでは、URL 内の ID を `:id` に置き換えます。

---

## POST `/api/v1/roles/self-batch`

ログインメンバーが、自分自身のロールを一括で付与・解除（バッチ更新）します。
Discord REST API のメンバーロール更新（`PATCH /guilds/{guild_id}/members/{user_id}`）および DB の割り当て更新を 1 回のリクエストでアトミックに適用します。

* **認可レベル**: `Member`（`member`, `sub_user`, `obog`, `admin`）
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "roles_to_add": ["123456789012345678"],
  "roles_to_remove": ["234567890123456789"]
}
```
※ `roles_to_add` と `roles_to_remove` はそれぞれ最大50件まで指定可能です。

### レスポンス (200 OK)
```json
{
  "ok": true,
  "discord_id": "123456789012345678",
  "added": ["123456789012345678"],
  "removed": ["234567890123456789"]
}
```
変更がなかった場合:
```json
{
  "ok": true,
  "added": [],
  "removed": [],
  "detail": "変更点はありませんでした"
}
```

### バリデーション & エラーレスポンス
- `400 Bad Request`:
  - 同一ロールが `roles_to_add` と `roles_to_remove` の両方に指定されている場合
  - Discord ID が特定できない場合
- `403 Forbidden`（ホワイトリスト方式。判定は DB のマニフェストを正とする）:
  - カテゴリ未設定（`category_id: null`）のロールが含まれる場合
  - 付与・解除できるカテゴリ（マニフェストに存在し、`is_restricted: false` かつ予約カテゴリ以外）に属さないロールが含まれる場合
  - マニフェスト上の `permissions` が `0` 以外（Discord 権限付き）のロールが含まれる場合
  - 付与対象ロールに、Discord のチャンネル権限上書きで何らかの権限許可（`allow != 0`）が設定されている場合。上書き一覧を取得できない場合は `502` で更新を中止します。解除は許可します。
  - Discord のマネージドロール（Bot/連携用）または `@everyone` ロールが含まれる場合
  - Bot メンバーが持つ最上位ロール以上の位置にあるロールが含まれる場合。Bot メンバーまたは基準ロールを特定できない場合も、誤操作防止のため拒否します。
- `404 Not Found`:
  - 指定されたロールがマニフェストまたは Discord サーバー上に存在しない場合
  - ギルドメンバーが見つからない場合
- `500 Internal Server Error`:
  - DB更新失敗時。Discord 上のロール変更は元の状態に自動補償ロールバックされます。
- `502 Bad Gateway`:
  - Discord API との通信エラー。

### Discord API の呼び出し
- 検証用ロール一覧（`GET /guilds/{guild_id}/roles`）、対象メンバーの現在のロール（`GET /guilds/{guild_id}/members/{user_id}`）、Bot メンバーの現在のロール（`GET /guilds/{guild_id}/members/{bot_user_id}`）、付与時のチャンネル上書き一覧（`GET /guilds/{guild_id}/channels`）は互いに依存しないため、並列に取得します。解除のみの場合はチャンネル上書きを取得しません。その後、ロールを一括更新（`PATCH /guilds/{guild_id}/members/{user_id}`）します。
- チャンネル上書きの `type` がロールである項目について、`allow` が `0` 以外のロールはセルフ付与できません。Discord 側のチャンネル権限設定を DB のマニフェストには同期しないため、付与リクエストごとに Discord の現在値を検査します。`deny` のみが設定されたロールは付与できます。
- Bot 自身のユーザー ID（`GET /users/@me`）はプロセスの稼働中に初回だけ取得し、以降はメモリ上のキャッシュを使います。Bot の操作可能範囲は統合ロールではなく、Bot メンバーが実際に持つロールの最上位位置を基準に判定します。
- Bot メンバーまたはそのロール階層を特定できない場合は、セルフロール操作を拒否し、push の割り当て変更をすべてスキップします。
- 並列に取得しても、取得結果の判定順は「ロール一覧の取得失敗（502）→ Bot メンバー情報の取得失敗（502）→ ロールの 403 / 404 検証 → 付与時のチャンネル上書き一覧の取得失敗（502）→ チャンネル上書きによる 403 検証 → 対象メンバー情報の取得失敗（502）」です。解除のみの場合、チャンネル上書き一覧の取得・検証は行いません。

---

## POST `/api/v1/roles/self-create`

ログインメンバーが、セルフ付与できるカテゴリ（ゲーム・スキルなど）に Discord 権限なしのロールを作成し、自分に付与します。
作成したロールは作成者個人のものではなく、サーバー全体で共有されます。他のメンバーも `self-batch` で付与・解除できます。編集・削除・並び替えは管理者が `/roles` の管理画面から行います。

* **認可レベル**: `Member`（`member`, `sub_user`, `obog`, `admin`）
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**:
```json
{
  "name": "Minecraft",
  "color": "#3498DB",
  "category_id": "cat-game"
}
```

| 項目 | 説明 |
|---|---|
| `name` | ロール名。前後の空白を除いて 1〜100 文字（Discord の上限） |
| `color` | `#rrggbb` 形式の色 |
| `category_id` | 作成先のカテゴリ ID。`self-batch` で付与・解除できるカテゴリ（マニフェストに存在し、`is_restricted: false` かつ予約カテゴリ以外）に限る |

`permissions` / `hoist` / `mentionable` は受け付けず、Backend で `permissions = 0`・`hoist = false`・`mentionable = true`（管理画面の新規作成と同じ既定値）に固定します。

### レスポンス (200 OK)
```json
{
  "ok": true,
  "role": {
    "role_id": "123456789012345678",
    "name": "Minecraft",
    "color": "#3498DB",
    "permissions": 0,
    "position": 1,
    "category_id": "cat-game"
  },
  "assigned": true
}
```
* `assigned`: 作成者への付与（Discord と DB の両方）まで完了したか。`false` の場合もロールは作成済みのため、通常のセルフ付与で付与できます。

### 処理の流れ
1. DB のマニフェストを正として、カテゴリと同名ロールの有無を検証します。
2. Discord にロールを作成します（`POST /guilds/{guild_id}/roles`）。Discord はロールを最下部に作るため、Bot の操作可能範囲に入ります。
3. Discord が返した実 ID で `role_manifests` に保存します。`position` は既存ロールの最小値の 1 つ下（1 未満にはしない）にします（管理画面の新規作成は Bot より下のロールだけから最小値を取りますが、最下位のロールは通常 Bot より下にあるため、結果は同じになります）。同名ロールの確認から保存までは、ロール作成同士で直列化します（`pg_advisory_xact_lock`）。
   * 保存に失敗した場合（同名ロールが直前に作られた場合を含む）は、作成した Discord のロールを削除します。
   * push はマニフェストにないロールを Discord から削除するため、Discord にだけロールが残ることはありません（削除にも失敗した場合は、次の push で削除されます）。
4. 作成者に付与します（`PUT /guilds/{guild_id}/members/{user_id}/roles/{role_id}` → `role_member_assignments`）。DB への保存に失敗した場合は Discord 側の付与を取り消し、`assigned: false` を返します。

### バリデーション & エラーレスポンス
- `400 Bad Request`: Discord ID が特定できない場合
- `403 Forbidden`: 作成先のカテゴリが存在しない、または `self-batch` で扱えないカテゴリの場合
- `409 Conflict`: 次のいずれかの場合（どちらも大文字・小文字と前後の空白の違いは無視）
  - 同じ名前のロールがすでにある場合
  - 予約名の場合。`/members/sync` はロール名で会員種別を判定するため、`backend/app/core/config.py` の `ADMIN_ROLE_NAMES` / `MEMBER_ROLE_NAMES` / `OBOG_ROLE_NAMES` / `SUB_USER_ROLE_NAMES` / `PRE_MEMBER_ROLE_NAME` に含まれる名前は作成できません
- `422 Unprocessable Entity`: ロール名・色・カテゴリ ID の形式が正しくない場合
- `429 Too Many Requests`: Discord ID ごとに 10 分間に 5 回を超えて呼び出した場合（`backend/app/core/config.py` の `ROLE_SELF_CREATE_RATE_LIMIT` / `ROLE_SELF_CREATE_RATE_WINDOW_SECONDS`）。`Retry-After` ヘッダーに待ち秒数を返します。
- `500 Internal Server Error`:
  - `DISCORD_TOKEN` が設定されていない場合
  - DB への保存に失敗した場合。Discord に作成したロールは削除されます（削除にも失敗した場合は、その旨を `detail` に返します）。
- `502 Bad Gateway`: Discord へのロール作成に失敗した場合。DB には何も保存しません。

---

## GET `/api/v1/roles/lists`

`user_memberships` に登録されているメンバーの一覧を種別（`member` / `sub_user` / `admin` / `pre_member` / `obog`）ごとに取得します。各一覧は `assigned_at` の新しい順です。

* **認可レベル**: `Admin`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`

### レスポンス (200 OK)
```json
{
  "member_list": [
    {
      "discord_id": "123456789012345678",
      "assigned_by": null,
      "assigned_at": "2026-04-01T12:00:00+00:00"
    }
  ],
  "sub_user_list": [],
  "admin_list": [],
  "pre_member_list": [],
  "obog_list": []
}
```

---

## GET `/api/v1/roles/me/assignments`

ログイン中のユーザー自身に割り当てられたロールだけを取得します。ほかのユーザーのDiscord IDや割り当て情報は返しません。

* **認可レベル**: `Member`（`member`, `sub_user`, `obog`, `admin`）
* **レスポンス (200 OK)**:
```json
{
  "assignments": {
    "123456789012345678": ["123456789012345678"]
  }
}
```

## GET `/api/v1/roles/members`

保存済みのギルドメンバー一覧と、全ロールの割り当て情報を取得します。

* **認可レベル**: `Admin`

### レスポンス (200 OK)
```json
{
  "members": [
    {
      "user_id": "12345678912345678912",
      "username": "taro_yamada",
      "display_name": "山田太郎",
      "avatar": "avatar_hash"
    }
  ],
  "assignments": {
    "987654321098765432": ["123456789012345678"]
  }
}
```

---

## POST `/api/v1/roles/members/sync`

特定ロールに所属するメンバーの割当を、Discord の実態から DB へ同期します。

同期時に Discord のギルドメンバーを全件取得し、同期対象のロールを持たないメンバー（Bot を含む）も含めた全員の名前・アイコンを `guild_members` に保存します。

`user_memberships` は種別（`member` / `sub_user` / `obog` / `admin` / `pre_member`）ごとに差分で同期します。Discord で対応するロールを持たなくなったユーザーの行だけを削除し、新しくロールを持ったユーザーの行だけを追加します。既存の行の `assigned_by` / `assigned_at` は変更しません。対応するロール（`sub_user` は `sub垢`）が Discord に見つからない種別は変更せず、警告ログを出します。

`sub垢` ロールを持つユーザーは、member ロールも持っていても `member` には含めず、`sub_user` としてのみ同期します（サブアカウントは Bot の reconcile で member ロールも付与されるため）。

Discord から取得したギルドメンバーが 0 件の場合は、取得に失敗したものとみなして同期を中止し、`502` を返します（`guild_members` / `user_memberships` は変更しません）。

レスポンスの各一覧（`member_list` / `sub_user_list` / `admin_list` / `pre_member_list` / `obog_list`）には、同期後のその種別の全行が入ります。

* **認可レベル**: `Admin`
* **リクエストボディ**: `{"role_id": "123456789012345678"}`

### レスポンス (200 OK)
```json
{
  "ok": true,
  "guild_id": "123456789012345678",
  "member_list": [
    {
      "discord_id": "123456789012345678",
      "membership_type": "member",
      "assigned_by": null,
      "assigned_at": "2026-04-01T12:00:00+00:00",
      "created_at": "2026-04-01T12:00:00+00:00"
    }
  ],
  "sub_user_list": [],
  "admin_list": [],
  "pre_member_list": [],
  "obog_list": []
}
```

---

## PATCH `/api/v1/roles/{role_id}/permissions`

ロールの Discord 権限ビットフラグを更新します。

* **認可レベル**: `Admin`
* **パスパラメータ**: `role_id` (string)
* **リクエストボディ**:
```json
{
  "permissions": 8
}
```
