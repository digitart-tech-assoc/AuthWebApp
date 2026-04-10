Survey responses table schema for 本入会アンケート

提案テーブル: `member_survey_responses`

用途: 本入会フォーム送信時に保存するアンケート回答を格納する。

主な要件:
- 1 レコードは一回の本入会フォーム送信（student_id もしくは student_number に紐付く）に対応
- 複数選択肢は配列/JSONで保存
- その他入力欄は個別カラムで保存
- 作成・更新タイムスタンプを保持

例: PostgreSQL 用 CREATE TABLE

```sql
CREATE TABLE member_survey_responses (
  id BIGSERIAL PRIMARY KEY,
  student_number VARCHAR(32) NOT NULL,
  -- JSONB fields to store multiple-choice selections
  digitart_channels JSONB DEFAULT '[]'::jsonb,
  digitart_channels_other TEXT,

  circle_search_channels JSONB DEFAULT '[]'::jsonb,
  circle_search_other TEXT,

  discord_invite_source TEXT,

  interested_fields JSONB DEFAULT '[]'::jsonb,
  interested_fields_other TEXT,

  motivations JSONB DEFAULT '[]'::jsonb,
  motivations_other TEXT,

  -- optional: store raw payload for audit/debug
  raw_payload JSONB,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- インデックス: student_number 検索や集計を想定
CREATE INDEX idx_member_survey_student_number ON member_survey_responses(student_number);

```

運用メモ:
- 複数選択肢は JSONB 配列で保存するため、集計は `jsonb_array_elements_text` 等で行える。
- `student_number` を外部キーで users テーブルに紐付ける場合は、ユーザー側の主キーに合わせて型/制約を追加する。
- 将来的に回答の履歴管理やバルク解析が必要になったら、raw_payload を有効活用する。
