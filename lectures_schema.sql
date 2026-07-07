-- ============================================================
-- lectures テーブル & RLS ポリシー (Supabase SQL Editor で実行)
-- ============================================================

-- btree_gist 拡張 (EXCLUDE USING gist に必要)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- lectures テーブル
CREATE TABLE IF NOT EXISTS lectures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  discord_name TEXT NOT NULL,
  notes TEXT,
  is_authenticated_booking BOOLEAN NOT NULL DEFAULT false,
  user_id TEXT REFERENCES users(user_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  -- 時間帯重複を DB レベルで防止
  CONSTRAINT lectures_no_overlap EXCLUDE USING gist (
    tstzrange(start_at, end_at, '[)') WITH &&
  ),

  -- 開始 < 終了の保証
  CONSTRAINT lectures_start_before_end CHECK (start_at < end_at),

  -- 対象期間内のみ許可（8月1日〜9月13日）
  CONSTRAINT lectures_in_period CHECK (
    start_at >= '2026-08-01 00:00:00+09'
    AND end_at <= '2026-09-14 00:00:00+09'
  )
);

-- updated_at を自動更新するトリガー関数
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER lectures_set_updated_at
  BEFORE UPDATE ON lectures
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- インデックス
CREATE INDEX IF NOT EXISTS idx_lectures_start_at ON lectures(start_at);
CREATE INDEX IF NOT EXISTS idx_lectures_end_at   ON lectures(end_at);
CREATE INDEX IF NOT EXISTS idx_lectures_user_id  ON lectures(user_id);

-- ============================================================
-- RLS ポリシー
-- ============================================================
ALTER TABLE lectures ENABLE ROW LEVEL SECURITY;

-- 誰でも閲覧可能（公開カレンダー）
CREATE POLICY "lectures_select_all"
  ON lectures FOR SELECT
  USING (true);

-- 誰でも作成可能（匿名ユーザー含む）
-- 重複チェックは EXCLUDE 制約 + API ルートで実施
CREATE POLICY "lectures_insert_all"
  ON lectures FOR INSERT
  WITH CHECK (true);

-- 本人のみ更新可能
CREATE POLICY "lectures_update_own"
  ON lectures FOR UPDATE
  USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);

-- 本人のみ削除可能
CREATE POLICY "lectures_delete_own"
  ON lectures FOR DELETE
  USING (auth.uid()::text = user_id);

-- ============================================================
-- 確認用クエリ
-- ============================================================
SELECT 'OK - lectures schema created' AS status;
