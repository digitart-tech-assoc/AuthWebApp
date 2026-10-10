# 在学生登録・学生認証 API 仕様 (`/api/v1/student`)

本ドキュメントは、在学生の本入会フローにおける適格性チェック、大学メールアドレス（`@aoyama.jp`）宛のワンタイムパスワード（OTP）送信・検証、および学生プロフィールの取得・保存に関する API 仕様です。

---

## POST `/api/v1/student/validate-eligibility`

ログイン中のユーザーが本入会手続きを行える状態かどうか（Discord連携済みか、仮入会ロールを所持しているか、部費支払い済みか）を判定します。

* **認可レベル**: `Authenticated`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
* **リクエストボディ**: なし

### レスポンス (200 OK)
```json
{
  "is_discord_linked": true,
  "is_pre_member": true,
  "is_paid": true,
  "can_register": true,
  "reason": "本入会手続きが可能です。"
}
```

* `can_register`: `false` の場合、フロントエンドで理由に応じたガイダンス（「まずはDiscordサーバーに参加してください」「入会費の支払い確認をお待ちください」等）を表示します。

---

## POST `/api/v1/student/otp/send`

学生番号を入力した際、大学メールアドレス（例: `c5624xxx@aoyama.jp`）を自動生成し、そのアドレス宛に 6 桁の確認コード（OTP）を送信します。

* **認可レベル**: `Authenticated`
* **リクエストボディ**:
```json
{
  "student_number": "1A241234",
  "name": "青山 太郎"
}
```

### レスポンス (200 OK)
```json
{
  "email_aoyama": "c5624123@aoyama.jp",
  "message": "大学メールアドレス宛に認証コードを送信しました。",
  "expires_in_seconds": 600
}
```

### エラーレスポンス (403 Forbidden)
入会資格（仮入会ロール所持かつ入会費支払い済み）を満たさない場合、処理を行わずに返却します。
```json
{ "detail": "入会予定者リストに登録されていません" }
```
* `detail` は `"入会予定者リストに登録されていません"` または `"入会費の支払いが確認できません"`。

---

## POST `/api/v1/student/otp/verify`

大学メール宛に届いた 6 桁の OTP コードを検証し、メール所有権の確認を完了します。

* **認可レベル**: `Authenticated`
* **リクエストボディ**:
```json
{
  "code": "582914"
}
```

### レスポンス (200 OK)
```json
{
  "verified": true,
  "message": "メール認証が完了しました。"
}
```

### エラーレスポンス (400 Bad Request)
次のいずれかの場合。`detail` に理由が入ります。
* コードが誤っている（`"Incorrect OTP code."`）。試行回数（`attempt_count`）を 1 増やす。
* コードの有効期限（10分）が切れている（`"OTP has expired. Please request a new one."`）。
* OTP が存在しない（`"No OTP found. Please request a new one."`）。

### エラーレスポンス (401 Unauthorized)
Discord アカウントが連携されていない場合（`"Discord account not linked"`）。

### エラーレスポンス (403 Forbidden)
入会資格（仮入会ロール所持かつ入会費支払い済み）を満たさない場合、OTP の照合（試行回数の消費）を行わずに返却します。
```json
{ "detail": "入会予定者リストに登録されていません" }
```
* `detail` は `"入会予定者リストに登録されていません"` または `"入会費の支払いが確認できません"`。

### エラーレスポンス (409 Conflict)
同じ OTP の検証が同時に行われており、行ロック（`SELECT ... FOR UPDATE`）の待ち時間が上限（`OTP_LOCK_TIMEOUT_MS` = 3 秒）を超えた場合。試行回数は消費しない。`detail` は `"同じ認証コードの確認が同時に行われています。しばらく待ってから再度お試しください。"`。

### エラーレスポンス (429 Too Many Requests)
試行回数上限（`attempt_count >= 5`）に達している場合（`"Too many attempts. Please request a new OTP."`）。5 回目の誤入力の時点でコードは失効する。

---

## GET `/api/v1/student/profile`

ログイン中のユーザーに紐づく登録済み学生プロフィールを取得します。

* **認可レベル**: `Authenticated`
* **リクエストヘッダー**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`

### レスポンス (200 OK)
```json
{
  "id": "prof-uuid-1234",
  "discord_id": "123456789012345678",
  "student_number": "1A241234",
  "name": "青山 太郎",
  "furigana": "アオヤマ タロウ",
  "department": "理工学部情報テクノロジー学科",
  "gender": "男性",
  "phone": "090-1234-5678",
  "email_aoyama": "c5624123@aoyama.jp",
  "email_verified": true,
  "otp_verified": true,
  "profile_submitted_at": "2026-03-28T12:00:00Z"
}
```

---

## POST `/api/v1/student/profile`

本入会フォームで入力された学生プロフィールを確定保存し、本入会登録を完了します。
※前提として、入会資格（仮入会ロール所持かつ入会費支払い済み）を満たし、事前の OTP 検証が完了している必要があります。
※既に `member` / `admin` / `obog` のユーザーはプロフィール更新として扱い、入会資格・OTP の検証を省略します。

* **認可レベル**: `Authenticated`
* **リクエストボディ**:
```json
{
  "student_number": "1A241234",
  "name": "青山 太郎",
  "furigana": "アオヤマ タロウ",
  "department": "理工学部情報テクノロジー学科",
  "gender": "男性",
  "phone": "090-1234-5678"
}
```

### レスポンス (200 OK)
保存された学生プロフィール情報が返却されます。

### エラーレスポンス
* `403 Forbidden`: 入会資格を満たさない（`detail` は上記 OTP 送信 API と同じ）。入会資格は本会員化と同一トランザクション内でも行ロック付きで再検証するため、事前確認後に支払情報の失効・削除や仮入会ロールの削除があった場合も 403 となり、プロフィール保存・会員ロール付与は行われない。
* `400 Bad Request`: OTP 検証が完了していない（`"OTP verification required"`）。
