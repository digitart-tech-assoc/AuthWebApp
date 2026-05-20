## 概要

本入会フォーム（`/join/member`）は、正式メンバーとしての登録を行う5ステップ詳細フォームページです。学生情報の入力・確認、アンケート回答、OTP認証を経て、最終的にメンバーとして登録されます。サーバーアクション、useEffect、複数のステップコンポーネントで構成されています。

## 主要要件

- 5 ステップの段階的フォーム
- 学生情報（学生番号・氏名・ふりがな・学部・性別・電話番号）入力
- サークル活動に関するアンケート
- OTP（メール認証）確認
- 完了画面表示

## 非機能要件

- クライアントコンポーネント（React フック使用）
- サーバーアクション統合
- ステップ間の状態管理
- エラーハンドリング
- 適格性チェック（eligibility）

## 必要項目・操作

### 5 ステップ構成

#### Step 1: 適格性確認
- ページロード時に `checkEligibility()` 実行
- 本入会可能か判定
- 不可の場合：詳細ガイダンス表示

#### Step 2: 基本情報入力
| 項目 | 型 | 必須 | 説明 |
|-----|-----|------|------|
| 学生番号 | string | ○ | 8 桁 |
| 氏名 | string | ○ | 姓名 |
| ふりがな | string | ○ | しめい |
| 学部 | string | ○ | 所属学部 |
| 性別 | select | × | 男性/女性/その他 |
| 電話番号 | string | ○ | 連絡先 |

#### Step 3: アンケート回答
- サークル活動への興味・参加意思
- スキルレベル
- その他オプション設問

#### Step 4: OTP 認証
- 登録メールアドレスにOTPを送信
- 6 桁OTPコード入力
- 認証確認

#### Step 5: 完了画面
- 仮入会完了メッセージ
- 次のステップへのナビゲーション（`/roles` など）

### アクセス制御
| 状態 | 動作 |
|------|------|
| 未認証 | `/login` へリダイレクト |
| 本入会不可 | Step 1 で詳細ガイダンス表示 |
| 本入会可 | Step 2 へ進む |

## 操作

1. **ページロード**
   - `checkEligibility()` 呼び出し
   - `getStudentProfile()` で既存情報取得
   - 適格性判定

2. **Step 1 → Step 2**
   - 「次へ」ボタン クリック
   - 基本情報入力フォーム表示

3. **Step 2: 基本情報入力 → Step 3**
   - 全項目入力（必須項目）
   - 「次へ」ボタン クリック
   - アンケート画面へ

4. **Step 3: アンケート → Step 4**
   - アンケート選択肢を選択
   - 「次へ」ボタン クリック
   - OTP 送信プロセス開始

5. **Step 4: OTP 認証 → Step 5**
   - OTP コード入力
   - 「認証」ボタン クリック
   - OTP 検証成功後、完了画面表示

6. **Step 5: 完了**
   - 完了メッセージ表示
   - 「ロール管理へ」ボタン → `/roles` へ遷移

### 戻る機能
- Step 2 から Step 1 へ戻る
- Step 3 から Step 2 へ戻る
- Step 4 から Step 3 へ戻る

## 仕様API

### Server Action: checkEligibility
**ファイル**: `/frontend/src/actions/student-registration.ts`

```typescript
async function checkEligibility(): Promise<EligibilityCheckResult>
```

**レスポンス**
```typescript
interface EligibilityCheckResult {
  can_register: boolean;
  reason?: string;
  pre_member_info?: {
    discord_id: string;
    assigned_at: string;
  };
}
```

### Server Action: getStudentProfile
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

### POST /api/survey
アンケート回答保存

**リクエスト**
```json
{
  "answers": {
    "interest_level": string,
    "participation_willingness": string,
    "skills": []
  }
}
```

**レスポンス**
```json
{ "success": true }
```

### POST /api/v1/members/member/add
本入会登録

**リクエスト**
```json
{
  "student_number": "string",
  "name": "string",
  "furigana": "string",
  "department": "string",
  "gender": "string | null",
  "phone": "string",
  "otp_code": "string"
}
```

**レスポンス**
```json
{
  "success": true,
  "user_id": "string",
  "message": "本入会が完了しました"
}
```

## 関連DB

- `student_profiles` テーブル
- `survey_responses` テーブル
- `members` テーブル
- `pre_members` テーブル
- OTP テーブル

## 備考

- 既に学生プロフィールがある場合は、フォームにプリフィル
- OTP は 登録メールアドレスに送信
- OTP 有効期限：15 分（推定）
- ステップ間の状態は React State で管理
- エラー時：エラーメッセージ表示、入力値保持

## 実装メモ

- `FormState` インターフェースで入力データ管理
- `useRouter` で完了後に `/roles` へナビゲート
- `useEffect` で初期化ロジック（適格性・プロフィール取得）
- コンポーネント分割：`FormStep1Eligibility`, `FormStep2Input`, `FormStep3Survey`, `FormStep4OTP`, `FormStep5Complete`
- `fetchBackend()` または `fetch()` で API 呼び出し
- アンケートデータは `/api/survey` にPOST後、Step 4 へ進む
- 最終登録は `/api/v1/members/member/add` でバックエンド 実行
