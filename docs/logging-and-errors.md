# ログ・エラー出力規約

本ドキュメントは、Backend・Discord Bot・Frontend が出力するログとエラーに、何を含めてよいかを定めます。
ログ出力・例外処理・エラーレスポンス・エラー表示を追加・変更するときは、本規約に従ってください。

---

## 1. 情報の分類

### 1.1. 個人情報（出力を禁止する）
次の情報は個人情報として扱い、ログとエラーに含めません。

| 情報 | 主な保存先・入力元 |
| :--- | :--- |
| 氏名・ふりがな | `student_profiles`、`join_requests`、お問い合わせフォーム |
| 電話番号 | `student_profiles` |
| 学生番号 | `student_profiles`、`member_survey_responses`、`join_requests.metadata` |
| メールアドレス（大学メールを含む） | `student_profiles.email_aoyama`、`join_requests`、`otp_records`、お問い合わせフォーム |
| Discord のユーザー名・表示名 | `guild_members`（`username`, `display_name`）、Discord API の応答 |
| 入会申請・プロフィール・アンケート・お問い合わせで本人が入力した内容 | `join_requests.metadata`、`student_profiles`、`member_survey_responses`、お問い合わせ本文 |

### 1.2. 秘密情報（出力を禁止する）
個人情報ではありませんが、漏れると不正利用につながるため、ログとエラーに含めません。

- OTP コード（一部分も含む）
- Supabase の JWT・`SHARED_SECRET`・Discord Bot トークン・API キーなどの認証情報

### 1.3. 個人情報として扱わないもの（出力してよい）
- Discord ID（ユーザー・ロール・ギルド・チャンネルのスノーフレーク ID）
- 内部 ID（`users.user_id` など）
- ロール名・カテゴリ名、件数、HTTP ステータス、処理名

Discord ID はログとエラーに含めてかまいません。ただし、通常のレスポンスで Discord ID を返す範囲は、各 API の認可レベルに従います（例: 全メンバーの Discord ID を返す `GET /api/v1/roles/members` は `Admin` のみ。[api/README.md](./api/README.md) の認可レベルを参照）。

---

## 2. 出力先ごとの規約

| 出力先 | 個人情報・秘密情報 | Discord ID | エラーの詳細（例外メッセージ・外部 API の応答本文・スタックトレース） |
| :--- | :--- | :--- | :--- |
| Backend のログ | 禁止 | 可 | 可（個人情報を含みうるものは除く。§3.1） |
| Discord Bot のログ | 禁止 | 可 | 可（個人情報を含みうるものは除く。§3.1） |
| Backend の API エラーレスポンス（`detail`・`errors` など） | 禁止 | 可 | **禁止**（詳細は Backend のログにのみ出す。§3.2） |
| Frontend の画面表示 | 禁止 | — | **禁止**（Frontend で定めた固定文言のみ表示する。§3.3） |
| Frontend の `console`（ブラウザ・Server Action・Route Handler） | 禁止 | — | **禁止**（§3.3） |

エラーの詳細は Backend（および Discord Bot）のログに集約し、調査はログで行います。

---

## 3. 実装上の注意

### 3.1. Backend・Discord Bot のログ
- 対象のユーザーは Discord ID で示してかまいません。
- 例外メッセージや外部 API の応答本文をログに出すときは、個人情報が含まれないかを確認してください。含まれうる場合は、HTTP ステータス・エラーコード・例外の型名など、個人情報を含まない項目だけを出します。
  - 例: Brevo（メール送信）の応答本文には宛先のメールアドレスが含まれることがある。
  - 例: DB の制約違反の例外メッセージには、`Key (email)=(...)` のように値が含まれることがある。
- お問い合わせ・入会申請などのリクエストボディをそのままログに出さないでください。

### 3.2. Backend の API エラーレスポンス
- `detail`・`errors` には、Backend で定めた固定文言と、ID・件数・HTTP ステータスなど §1.3 の情報だけを含めます。
- `str(e)` などの例外メッセージ、外部 API（Discord・Brevo 等）の応答本文、スタックトレースは含めません。これらは Backend のログに出します。

### 3.3. Frontend
- Backend から返された `detail`・`errors` などの文言を、そのまま画面に表示しないでください。画面には Frontend で定めた固定文言（例: 「送信に失敗しました。時間をおいて再度お試しください」）を表示します。HTTP ステータスなどで文言を出し分けるのはかまいません。
- Backend から返されたエラーの詳細を `console.log` / `console.error` に出さないでください（Server Action・Route Handler で出すとコンテナログに残ります）。
