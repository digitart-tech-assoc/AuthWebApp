"""役割: DDL管理・マイグレーション

init_db() 関数を repository.py から分離。
テーブル作成とスキーママイグレーションを担当。
"""

from __future__ import annotations

import sys

from app.db.connection import _connect


def init_db() -> None:
    """初期テーブルを作成する。DBに接続できない場合は警告を出して終了しない。"""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                # Ensure pgcrypto extension is available for gen_random_uuid().
                # Ignore failures (hosted providers may restrict extension creation).
                try:
                    cur.execute("SAVEPOINT create_pgcrypto;")
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
                    cur.execute("RELEASE SAVEPOINT create_pgcrypto;")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT create_pgcrypto;")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS role_categories (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        display_order INTEGER DEFAULT 0,
                        is_collapsed BOOLEAN DEFAULT FALSE,
                        permissions BIGINT DEFAULT 0
                    );
                    """
                )
                # Migration: add permissions column if it was created without it
                cur.execute(
                    """
                    ALTER TABLE role_categories ADD COLUMN IF NOT EXISTS permissions BIGINT DEFAULT 0;
                    """
                )
                # Migration: add is_restricted column (admin-only category flag)
                cur.execute(
                    """
                    ALTER TABLE role_categories ADD COLUMN IF NOT EXISTS is_restricted BOOLEAN DEFAULT FALSE;
                    """
                )
                # Migration: update default restricted categories to TRUE
                cur.execute(
                    """
                    UPDATE role_categories SET is_restricted = TRUE WHERE name IN ('会員情報', '学部学科', '学年');
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS role_manifests (
                        role_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        color TEXT DEFAULT '#000000',
                        hoist BOOLEAN DEFAULT FALSE,
                        mentionable BOOLEAN DEFAULT FALSE,
                        permissions BIGINT DEFAULT 0,
                        position INTEGER NOT NULL,
                        category_id TEXT REFERENCES role_categories(id) ON DELETE SET NULL,
                        is_managed_by_app BOOLEAN DEFAULT TRUE,
                        is_our_bot BOOLEAN DEFAULT FALSE,
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )

                # アプリユーザー RBAC（Supabase auth UUID をキーとして使用）
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        user_id TEXT UNIQUE NOT NULL,
                        discord_id TEXT UNIQUE,
                        app_role TEXT NOT NULL DEFAULT 'none'
                            CHECK (app_role IN ('member', 'admin', 'obog', 'pre_member', 'none')),
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )

                # 入会費支払い済みリスト（adminが管理、discord_idで照合）
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS paid_invitations ( 
                        id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        discord_id TEXT UNIQUE NOT NULL,
                        user_id TEXT,
                        note TEXT,
                        expires_at TIMESTAMPTZ,
                        assigned_by TEXT,
                        assigned_at TIMESTAMPTZ DEFAULT now(),
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                # Migration: add assigned_by and assigned_at columns if missing
                cur.execute(
                    """
                    ALTER TABLE paid_invitations ADD COLUMN IF NOT EXISTS user_id TEXT;
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE paid_invitations ADD COLUMN IF NOT EXISTS assigned_by TEXT DEFAULT 'unknown';
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE paid_invitations ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ DEFAULT now();
                    """
                )
                # 既存の NULL 値を 'unknown' に更新
                cur.execute(
                    """
                    UPDATE paid_invitations SET assigned_by = 'unknown' WHERE assigned_by IS NULL;
                    """
                )

                # 統合メンバーシップテーブル（member / admin / pre_member / obog）
                cur.execute(
					"""
					CREATE TABLE IF NOT EXISTS user_memberships (
						discord_id TEXT NOT NULL,
						membership_type TEXT NOT NULL 
							CHECK (membership_type IN ('member', 'admin', 'pre_member', 'obog', 'sub_user')),
						assigned_by TEXT,
						assigned_at TIMESTAMPTZ DEFAULT now(),
						created_at TIMESTAMPTZ DEFAULT now(),
						PRIMARY KEY (discord_id, membership_type),
						FOREIGN KEY (discord_id) REFERENCES guild_members(user_id) ON DELETE CASCADE
					);
					"""
				)
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_memberships_discord_id 
                    ON user_memberships (discord_id);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_memberships_membership_type 
                    ON user_memberships (membership_type);
                    """
                )

                # ビュー: ユーザーの app_role を user_memberships から動的に計算
                cur.execute(
					"""
					CREATE OR REPLACE VIEW v_users_with_app_role AS
					SELECT 
						u.id,
						u.user_id,
						u.discord_id,
						CASE 
							WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type = 'admin') 
								THEN 'admin'
							WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type IN ('member','sub_user')) 
								THEN 'member'
							WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type = 'obog') 
								THEN 'obog'
							WHEN EXISTS (SELECT 1 FROM user_memberships WHERE discord_id = u.discord_id AND membership_type = 'pre_member') 
								THEN 'pre_member'
							ELSE 'none'
						END as app_role,
						u.created_at,
						u.updated_at
					FROM users u
					"""
				)

                # Migration: Drop app_role from users table (now calculated via v_users_with_app_role VIEW)
                # This is a safe migration that preserves data
                try:
                    cur.execute(
                        """
                        ALTER TABLE users DROP COLUMN IF EXISTS app_role;
                        """
                    )
                except Exception as e:
                    # Column may already be dropped or table may be in use
                    pass
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS guild_members (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        display_name TEXT,
                        avatar TEXT,
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS role_member_assignments (
                        role_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        PRIMARY KEY (role_id, user_id)
                    );
                    """
                )
                # join_requests table for OTP-based join flow
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS join_requests (
                        id TEXT PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        form_type TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        metadata JSONB,
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_join_requests_email ON join_requests (email);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_join_requests_status ON join_requests (status);
                    """
                )
                # otp_codes table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS otp_codes (
                        id TEXT PRIMARY KEY,
                        join_request_id TEXT NOT NULL REFERENCES join_requests(id) ON DELETE CASCADE,
                        code_hash TEXT NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        verified_at TIMESTAMPTZ,
                        attempt_count INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_otp_codes_join_request_id ON otp_codes (join_request_id);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_otp_codes_expires_at ON otp_codes (expires_at);
                    """
                )
                conn.commit()
    except Exception as e:
        print(f"WARNING: init_db failed: {e}", file=sys.stderr)
        return
