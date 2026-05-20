## 概要

ログインページ（`/login`）は Discord 認証の入口です。Supabase を使用した Discord OAuth フローを開始し、ユーザーを Discord 認証ページへ誘導します。認証失敗時はエラーメッセージを表示します。

## 主要要件

- Discord OAuth 認証フロー開始
- 認証後のコールバック先（`callbackUrl`）を指定可能
- 認証失敗時のエラーハンドリング
- 認証コード交換とセッション作成
- アクセス権限がない場合のリダイレクト

## 非機能要件

- 完全サーバーサイドレンダリング
- セッション情報は Supabase クッキーで管理
- 認証状態の永続化

## 必要項目・操作

### クエリパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `callbackUrl` | string | × | 認証成功後の遷移先。デフォルト `/roles` |
| `error` | string | × | エラーコード。`auth_callback_error`, `discord_email_required` など |

### エラーメッセージ
| error コード | メッセージ |
|-----------|----------|
| `auth_callback_error` | 認証に失敗しました。もう一度お試しください。 |
| `discord_email_required` | Discord アカウントにメールアドレスが登録されていないため、ログインできません。 |
| その他 | エラーが発生しました。 |

## 操作

1. **ページ表示時**
   - エラーメッセージがあれば表示
   - Discord ログインボタンを表示

2. **Discord ログインボタン クリック**
   - `/auth/login/discord?callbackUrl=...` へリダイレクト
   - ユーザーを Discord 認可画面へ誘導

3. **ログイン処理**
   - Discord より OAuth コードを取得
   - `/auth/callback?code=...` でセッション交換
   - セッション作成後、`callbackUrl` へリダイレクト

## 仕様API

利用API：なし（SSR レンダリングのみ）

## 関連DB

- Supabase `auth` テーブル（セッション管理）

## 備考

- Discord アカウントにメールアドレスが登録されていない場合、ログインは失敗します
- `callbackUrl` のデフォルト値は `/roles`（ロール管理ページ）
- 本ページは未認証ユーザー向け

## 実装メモ

- エラーメッセージの条件分岐で `error` パラメータをチェック
- `callbackUrl` はURL エンコーディング必須
- Supabase OAuth は Discord との通信時にネットワーク遅延の可能性あり
