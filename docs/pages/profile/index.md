## 概要

プロフィールページ（`/profile`）は、認証済みメンバー向けの学生情報編集ページです。学生番号、氏名、ふりがな、学部、性別、電話番号などの個人情報を管理します。サーバーサイドで認可チェックを行い、メンバー以上の権限がある場合のみアクセスを許可します。

## 主要要件

- 学生プロフィール情報の表示・編集
- ユーザー認証チェック（未認証時はログインへリダイレクト）
- バックエンド認可チェック（`app_role` が member/admin/obog であることを確認）
- プロフィール情報の取得・更新
- フォームベースのUI（ProfileForm コンポーネント）

## 非機能要件

- サーバーサイドレンダリング
- ルート保護：middleware と SSR 両方で実装
- セッションベース認可（Supabase + バックエンド API）

## 必要項目・操作

### プロフィール編集項目
| 項目 | 型 | 必須 | 説明 |
|-----|-----|------|------|
| 学生番号 | string | ○ | 学籍番号 |
| 氏名 | string | ○ | 姓名 |
| ふりがな | string | ○ | 氏名のふりがな |
| 学部 | string | ○ | 所属学部 |
| 性別 | select | × | 男性/女性/その他 |
| 電話番号 | string | × | 連絡先電話番号 |

### アクセス制御
| ユーザー状態 | 動作 |
|-----------|------|
| 未認証 | `/login?callbackUrl=%2Fprofile` へリダイレクト |
| 認証済みだが member/admin/obog ではない | `/login?callbackUrl=%2Fprofile` へリダイレクト |
| member/admin/obog | ページ表示、プロフィール編集可能 |

## 操作

1. **ページアクセス時**
   - Supabase より現在ユーザー情報を取得
   - 未認証の場合：ログインページへリダイレクト
   - バックエンド `/api/v1/auth/me` より `app_role` を取得
   - `app_role` が member/admin/obog でない場合：ログインページへリダイレクト

2. **プロフィール表示**
   - 既存プロフィールがあれば取得して表示
   - 初回アクセス時は空フォーム

3. **情報編集・保存**
   - フォーム入力フィールドで編集
   - 保存ボタン クリック
   - `ProfileForm` コンポーネントがバックエンド へ POST/PUT 送信

## 仕様API

### GET /api/v1/auth/me
認可ヘッダ付きで呼び出し、ユーザー権限情報を取得

**レスポンス**
```json
{
  "app_role": "member" | "admin" | "obog" | "pre_member" | "none",
  "discord_id": "string | null",
  "display_name": "string",
  "avatar": "string"
}
```

### サーバーアクション：getStudentProfile
**ファイル**: `/frontend/src/actions/student-registration.ts`

```typescript
async function getStudentProfile(): Promise<StudentProfile | null>
```

**レスポンス**
```typescript
interface StudentProfile {
  student_number: string;
  name: string;
  furigana: string;
  department: string;
  gender?: string | null;
  phone: string;
}
```

## 関連DB

- `student_profiles` テーブル（バックエンド）
- `users` テーブル（Supabase）

## 備考

- ページは認証済みメンバーのみアクセス可能
- 権限チェックはサーバーサイドで実行（セキュリティ）
- 初回アクセスしたユーザーはプロフィール未登録
- プロフィール更新後は確認メッセージを表示

## 実装メモ

- `getBackendAuthorizationHeader()` で Authorization ヘッダを自動生成
- `resolveRoleFromBackend()` でバックエンド API から権限を取得
- `ProfileForm` はクライアントコンポーネント（フォーム操作用）
- ページレイアウト：`join.module.css` の共通スタイル使用
