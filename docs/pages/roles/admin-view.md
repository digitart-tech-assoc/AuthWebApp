# ロール管理 管理者表示仕様 (`RoleAccordion`)

本ドキュメントは、管理者（`app_role === "admin"` または `"obog"`）としてログインした際に `/roles` で表示される全体ロール管理ビュー（`RoleAccordion`）の画面要件・操作仕様です。

---

## 1. 概要
管理者はサークル内の Discord ロール階層、カテゴリ分け、ロールプロパティ（名前・色・権限）、およびメンバー個別割当をGUI上で直感的に編集・管理できます。
編集内容はブラウザ上で一時保持され、「差分プレビュー」を確認した上で Discord サーバーへ一括反映（Push）可能です。

---

## 2. 画面構成と機能モジュール

1. **カテゴリ・ロールアコーディオン（`SortableCategoryItem`, `RoleList`）**:
   - `@dnd-kit/core` および `@dnd-kit/sortable` によるドラッグ＆ドロップ。
   - カテゴリの並び替え、ロールの階層並び替え、カテゴリ間でのロール移動。
2. **新規ロール作成モーダル（`NewRoleModal`）**:
   - ロール名、カラーコード（プリセット/HEX入力）、hoist（別枠表示）、mentionable（メンション可否）、初期所属カテゴリの指定。
3. **メンバー割当モーダル（`RoleMemberModal`）**:
   - ロールごとの所属メンバー一覧表示、ニックネーム/ID 検索。
   - メンバーに対する個別ロールの付与・剥奪。
4. **権限ビットエディタ（`PermissionEditor`）**:
   - 管理者、チャンネル管理、メッセージ送信、VC接続等の Discord 権限ビットフラグをトグルスイッチで編集。
5. **カテゴリ管理モーダル（`EditCategoryModal`）**:
   - カテゴリ名の変更、一般メンバー編集禁止（`is_restricted`）の切替。
6. **差分プレビューモーダル（`RoleDiffModal`）**:
   - ローカル変更とサーバー（Discord/DB）上の現在状態を比較し、作成・更新・削除・並び替えの差分を一覧表示。
7. **同期・反映アクションバー（`PushButton`, `SyncButton`）**:
   - **DiscordへPush**: マニフェスト差分（`ManifestPatch`）をバックエンドへ保存し、Discord Bot を通じて Discord サーバーへ反映。
   - **Discordから同期**: Discord 側の最新ロール状態をフェッチし、画面表示をリフレッシュ。

---

## 3. 仕様API（フロントエンド Route Handlers 経由）

- **マニフェスト差分保存**: `PATCH /api/manifest`
  - バックエンド `PATCH /api/v1/manifest` を呼び出し。
- **Discord への差分 Push**: `POST /api/roles/push`
  - バックエンド `POST /api/v1/roles/push` または `sync` を呼び出し。
- **ロールメンバー一覧取得**: `GET /api/roles/members`
- **ロール権限更新**: `POST /api/roles/[roleId]/permissions`
