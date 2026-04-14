#!/usr/bin/env python
"""DB スキーマ移行：テーブル作成 スクリプト"""

import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Database URL configured: {DATABASE_URL is not None}")

try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=5, sslmode="require")
    with conn.cursor() as cur:
        # Check if guild_members exists
        cur.execute("""SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='guild_members');""")
        guild_members_exists = cur.fetchone()[0]
        print(f"guild_members テーブル存在: {guild_members_exists}")
        
        # Create user_memberships table
        print("user_memberships テーブルを作成中...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_memberships (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            discord_id TEXT NOT NULL,
            membership_type TEXT NOT NULL CHECK (membership_type IN ('member', 'admin', 'pre_member', 'obog')),
            assigned_by TEXT,
            assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            UNIQUE (discord_id, membership_type)
        );
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_memberships_membership_type ON user_memberships(membership_type);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_memberships_discord_id ON user_memberships(discord_id);")
        
        # Check if view exists
        cur.execute("""SELECT EXISTS(SELECT 1 FROM information_schema.views WHERE table_name='v_users_with_app_role');""")
        view_exists = cur.fetchone()[0]
        print(f"v_users_with_app_role VIEW 存在: {view_exists}")
        
        # Create SQL view for v_users_with_app_role
        if not view_exists:
            print("SQL VIEW v_users_with_app_role を作成中...")
            cur.execute("""
            CREATE OR REPLACE VIEW v_users_with_app_role AS
            SELECT 
                u.id,
                u.user_id,
                u.discord_id,
                CASE 
                    WHEN EXISTS (SELECT 1 FROM user_memberships 
                                 WHERE discord_id = u.discord_id 
                                 AND membership_type = 'admin')
                        THEN 'admin'
                    WHEN EXISTS (SELECT 1 FROM user_memberships 
                                 WHERE discord_id = u.discord_id 
                                 AND membership_type = 'member')
                        THEN 'member'
                    WHEN EXISTS (SELECT 1 FROM user_memberships 
                                 WHERE discord_id = u.discord_id 
                                 AND membership_type = 'pre_member')
                        THEN 'pre_member'
                    WHEN EXISTS (SELECT 1 FROM user_memberships 
                                 WHERE discord_id = u.discord_id 
                                 AND membership_type = 'obog')
                        THEN 'obog'
                    ELSE 'none'
                END as app_role,
                u.created_at,
                u.updated_at
            FROM users u;
            """)
        
        cur.execute("""SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='user_memberships');""")
        user_memberships_exists = cur.fetchone()[0]
        print(f"user_memberships テーブル作成状況: {user_memberships_exists}")
        
        conn.commit()
        print("✓ テーブル作成完了")
except Exception as e:
    print(f"✗ エラー: {e}")
    import traceback
    traceback.print_exc()
finally:
    if conn:
        conn.close()
