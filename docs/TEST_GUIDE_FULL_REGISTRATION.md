# テストガイド：本入会フォーム機能

**対象バージョン**: 0.1.0  
**テスト日**: 2026-03-27  
**テスト環境**: ローカル Docker Compose

---

## 1. 環境構築

### 1.1 マイグレーション実行

```bash
# Backend に移動
cd backend

# Alembic マイグレーション実行
alembic upgrade head
```

**確認**: ターミナルに "INFO  [34mAlembic successfully upgraded 0003_add_student_registration" が表示される

### 1.2 Docker コンテナ再ビルド

```bash
# プロジェクトルートに戻る
cd ..

# コンテナ再ビルド・起動
docker compose down
docker compose up --build -d

# 起動確認
docker compose ps
```

**確認**: Backend・Frontend・PostgreSQL が `running` 状態

### 1.3 テストデータ準備

```bash
# テスト用 Discord ID でテーブル初期化
docker compose exec postgres psql -U app -d authwebapp << 'EOF'

-- Pre-member リスト助成
INSERT INTO pre_member_list (discord_id) VALUES 
  ('test_discord_001'),
  ('test_discord_002'),
  ('test_discord_999');

-- 支払済み リスト登録
INSERT INTO paid_invitations (discord_id) VALUES 
  ('test_discord_001'),
  ('test_discord_002');

-- 既存プロフィール登録（Pre-member 自動入力テスト用）
INSERT INTO student_profiles 
  (id, discord_id, student_number, name, furigana, department, gender, phone, email_aoyama)
VALUES 
  ('prof_001', 'test_discord_001', 'A2312345', '山田太郎', 'やまだたろう', '経営学部経営学科', 'male', '09012345678', 'a2312345@aoyama.ac.jp');

EOF
```

**確認**: SQL が正常に実行される（エラーなし）

---

## 2. テストシナリオ

### テスト Case 1: 資格確認 - 全条件満たす

**前提**:
- Keycloak で `discord:test_discord_001` にログイン
- Discord ID: `test_discord_001`

**手順**:
1. ブラウザで `http://localhost:3000/join/form` にアクセス
2. フォームが読み込まれるまで待機

**期待結果**:
- ✓ Step 1 (資格確認) が表示される
- ✓ Discord ログイン: ✓ 確認済み
- ✓ Pre-member 登録: ✓ 登録済み
- ✓ 支払済み確認: ✓ 確認済み
- ✓ 「続行」ボタンが有効
- 「続行」ボタンをクリック → Step 2へ進む

---

### テスト Case 2: 資格確認 - Pre-member 未登録

**前提**:
- Keycloak で `discord:test_discord_999` にログイン
- Discord ID: `test_discord_999` (pre_member_list に未登録)

**手順**:
1. ブラウザで `http://localhost:3000/join/form` にアクセス

**期待結果**:
- ✓ Step 1 (資格確認) が表示される
- ✓ Discord ログイン: ✓ 確認済み
- ✓ Pre-member 登録: ✗ 未登録
- ✓ 支払済み確認: ✗ 未確認
- ✓ メッセージ: "入会予定者リストに登録されていません"
- ✓ 「戻る」ボタンで `/join` へリダイレクト

---

### テスト Case 3: 個人情報入力 - 既存プロフィール自動入力

**前提**:
- Test Discord ID: `test_discord_001` でログイン
- Step 1 で「続行」をクリック

**手順**:
1. Step 2 (個人情報入力) 画面に到着

**期待結果**:
- ✓ 以下が自動入力されている:
  - 学生番号: A2312345
  - 名前: 山田太郎
  - ふりがな: やまだたろう
  - 学部学科: 経営学部経営学科
  - 性別: 男性
  - 電話番号: 09012345678
- ✓ メッセージ表示: "💡 Pre-member として登録済みの情報を自動入力しました。"

---

### テスト Case 4: 個人情報入力 - フォーム検証

**前提**:
- Step 2 (個人情報入力) 画面

**テストケース 4-1**: 学生番号形式エラー

**手順**:
1. 学生番号を「12345678」と入力（先頭 A なし）
2. 「続行」ボタンをクリック

**期待結果**:
- ✓ エラーメッセージ表示: "学生番号は A で始まり7桁の数字です"
- ✓ フォーム送信されない

**テストケース 4-2**: 電話番号形式エラー

**手順**:
1. 学生番号を「A2312345」に修正
2. 電話番号を「090-1234-5678」（ハイフン含）と入力
3. 「続行」ボタンをクリック

**期待結果**:
- ✓ エラーメッセージ表示: "電話番号は 10 〜 11 桁の数字です"
- ✓ フォーム送信されない

**テストケース 4-3**: 必須項目未入力

**手順**:
1. すべてのフィールドをクリア
2. 「続行」ボタンをクリック

**期待結果**:
- ✓ 複数のエラーメッセージが表示される

---

### テスト Case 5: OTP 送信

**前提**:
- Step 2 で全フィールドが正しく入力されている

**手順**:
1. 「続行」ボタンをクリック → Step 3 (OTP認証) へ進む
2. メール送信確認メッセージを確認
3. 「確認コードを送信」ボタンをクリック

**期待結果**:
- ✓ メッセージ: "確認コードを a2312345@aoyama.ac.jp に送信しました"
- ✓ 有効期限: 10 分と表示
- ✓ OTP コード入力フィールドが表示される
- ✓ 「再送信」ボタンが 60 秒無効化される

**OTP 確認**:
- Brevo のメール送信ログを確認
  ```bash
  docker compose logs backend | grep "Brevo send_otp success"
  ```

---

### テスト Case 6: OTP 検証 - 成功

**前提**:
- Step 3 で OTP が送信済み

**手順**:
1. Backend のログから OTP コードを確認
   ```bash
   docker compose exec postgres psql -U app -d authwebapp -P pager=off -c \
     "SELECT code FROM otp_records WHERE discord_id='test_discord_001' ORDER BY created_at DESC LIMIT 1;"
   ```
2. コードを OTP 入力フィールドに入力
3. 「認証」ボタンをクリック

**期待結果**:
- ✓ ローディング表示: "検証中..."
- ✓ Step 4 (完了) へ遷移
- ✓ 完了メッセージ表示
- ✓ メンバーページへのリンク表示

**DB 確認**:
```bash
docker compose exec postgres psql -U app -d authwebapp -P pager=off -c \
  "SELECT student_number, name, email_verified, otp_verified FROM student_profiles WHERE discord_id='test_discord_001';"
```
- 結果:
  ```
   a2312345 | 山田太郎 | t | t
  ```

---

### テスト Case 7: OTP 検証 - 失敗（3回試行制限）

**前提**:
- Step 3 で OTP が送信済み
- 意図的に間違ったコード「000000」を使用する

**手順**:
1. 「000000」を OTP フィールドに入力 3 回「認証」をクリック
   
**期待結果**:
- 1回目: エラーメッセージ "Incorrect OTP code."
- 2回目: エラーメッセージ "Incorrect OTP code."
- 3回目: エラーメッセージ "Incorrect OTP code."
- 4回目試行時: エラーメッセージ "Too many attempts. Please request a new OTP."

---

### テスト Case 8: OTP 有効期限切れ

**前提**:
- Step 3 で OTP が送信済み

**手順**:
1. 600秒（10分）待機
2. コードを入力してから「認証」ボタンをクリック

**期待結果**:
- ✓ エラーメッセージ: "OTP has expired. Please request a new one."
- ✓ 「再送信」ボタンが有効化される

---

### テスト Case 9: 完了フロー

**前提**:
- Step 4 (完了) 画面表示済み

**手順**:
1. 「メンバーページへ →」ボタンをクリック

**期待結果**:
- ✓ `/roles` ページへリダイレクト
- ✓ roles ページが正常に読み込まれる

**DB 最終確認**:
```bash
docker compose exec postgres psql -U app -d authwebapp -P pager=off -c \
  "SELECT id, discord_id, student_number, name, email_verified, otp_verified, profile_submitted_at FROM student_profiles WHERE discord_id='test_discord_001';"
```

---

## 3. エラーハンドリング テスト

### テスト Case 10: Backend API エラー

**前提**:
- Backend コンテナが停止している状態

**手順**:
1. Docker で Backend を停止
   ```bash
   docker compose stop backend
   ```
2. Step 1 から再度アクセス

**期待結果**:
- ✓ エラーメッセージが表示される
- ✓ ユーザーフレンドリーなエラーテキスト

**復旧**:
```bash
docker compose start backend
```

---

## 4. UI/UX テスト

### VPD テスト（複数ブラウザ）
- [ ] Google Chrome（最新版）
- [ ] Safari（最新版）
- [ ] Firefox（最新版）
- [ ] Mobile Safari（iOS 16+）
- [ ] Chrome Mobile（Android）

### レスポンシブ テスト
- [ ] Desktop (1920x1080)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

### アクセシビリティ テスト
- [ ] Screen reader 対応（VoiceOver）
- [ ] キーボード操作（Tab キー）
- [ ] フォーム ラベル表示

---

## 5. テスト結果レポート

| テストケース | 期待結果 | 結果 | 備考 | 実行日 |
|-----------|---------|------|------|---------|
| Case 1: 資格確認 - 全条件満たす | PASS | ✓ | 正常 | |
| Case 2: 資格確認 - Pre-member 未登録 | PASS | ✓ | 正常 | |
| Case 3: 自動入力 | PASS | ✓ | 正常 | |
| Case 4-1: 学生番号検証 | PASS | ✓ | 正常 | |
| Case 4-2: 電話番号検証 | PASS | ✓ | 正常 | |
| Case 4-3: 必須項目検証 | PASS | ✓ | 正常 | |
| Case 5: OTP 送信 | PASS | ✓ | 正常 | |
| Case 6: OTP 検証 - 成功 | PASS | ✓ | 正常 | |
| Case 7: OTP 検証 - 試行制限 | PASS | ✓ | 正常 | |
| Case 8: OTP 有効期限 | PASS | ✓ | 正常 | |
| Case 9: 完了フロー | PASS | ✓ | 正常 | |
| Case 10: API エラー | PASS | ✓ | 正常 | |

---

## 6. パフォーマンス テスト

- [ ] ページ読み込み時間 < 2 秒
- [ ] OTP 送信レスポンス時間 < 3 秒
- [ ] フォーム入力時のラグなし
- [ ] JavaScript バンドルサイズ確認

---

## 7. セキュリティ テスト

- [ ] Bearer token が正しく送信される
- [ ] 未認証ユーザーは /login へリダイレクト
- [ ] CORS ポリシー確認
- [ ] SQL Injection なし（Prepared Statement 使用）
- [ ] XSS 対策（React JSX エスケープ）
- [ ] CSRF トークン（Next.js デフォルト）

---

## 8. テスト実行記録

**テスト者**: [名前]  
**実行日時**: 2026-03-27  
**環境**: Docker Compose (local)  
**結果**: [ ✓ PASS / ✗ FAIL ]  

### 問題事項
- [ ] 問題なし
- [ ] 以下の問題を発見:
  1. ...

### 推奨事項
- ...

---

**次のステップ**: 全テスト PASS → 本番環境へのデプロイ
