#!/usr/bin/env python3
"""
診断スクリプト: member_list と Discord role_member_assignments の不一致を調査
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables from .env file
def load_env_file(filepath="../.env"):
    if os.path.exists(filepath):
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip('"').strip("'")
                    os.environ[key.strip()] = value
    
load_env_file()

DATABASE_URL = os.getenv("DATABASE_URL")
MEMBER_ROLE_ID = os.getenv("MEMBER_ROLE_IDS", "").split(",")[0].strip()

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in .env")
    sys.exit(1)

if not MEMBER_ROLE_ID:
    print("❌ Error: MEMBER_ROLE_IDS not found in .env")
    sys.exit(1)

print(f"🔍 Diagnostic Report: Member List Synchronization")
print(f"=" * 60)
print(f"Database: {DATABASE_URL[:50]}...")
print(f"Member Role ID: {MEMBER_ROLE_ID}")
print(f"=" * 60)
print()

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. member_list のレコード数と内容
    print("📋 1. member_list テーブルの内容")
    print("-" * 60)
    cur.execute("SELECT COUNT(*) as count FROM member_list")
    member_list_count = cur.fetchone()["count"]
    print(f"   Total records: {member_list_count}")
    
    cur.execute("""
        SELECT discord_id, assigned_by, assigned_at, created_at
        FROM member_list
        ORDER BY assigned_at DESC
    """)
    member_list_records = cur.fetchall()
    member_list_ids = {row["discord_id"] for row in member_list_records}
    
    print(f"   Discord IDs in member_list:")
    for i, row in enumerate(member_list_records, 1):
        print(f"     {i:3d}. {row['discord_id']:20s} assigned_by={row['assigned_by']}, assigned_at={row['assigned_at']}")
    
    print()
    
    # 2. role_member_assignments から member ロール持ちユーザー数
    print("📋 2. Discord member ロール割り当て（role_member_assignments）")
    print("-" * 60)
    cur.execute("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM role_member_assignments 
        WHERE role_id = %s
    """, (MEMBER_ROLE_ID,))
    member_role_count = cur.fetchone()["count"]
    print(f"   Total Discord member role users: {member_role_count}")
    
    cur.execute("""
        SELECT user_id
        FROM role_member_assignments
        WHERE role_id = %s
        ORDER BY user_id
    """, (MEMBER_ROLE_ID,))
    discord_member_ids = {row["user_id"] for row in cur.fetchall()}
    
    print(f"   Discord IDs with member role:")
    for i, user_id in enumerate(sorted(discord_member_ids), 1):
        print(f"     {i:3d}. {user_id}")
    
    print()
    
    # 3. 不一致分析
    print("📋 3. 不一致分析")
    print("-" * 60)
    
    only_in_db = member_list_ids - discord_member_ids
    only_in_discord = discord_member_ids - member_list_ids
    both = member_list_ids & discord_member_ids
    
    print(f"   ✓ 両方に存在（正常）: {len(both)} 件")
    print(f"   ❌ DB にのみ存在（要確認）: {len(only_in_db)} 件")
    print(f"   ⚠️  Discord にのみ存在（DBに追加が必要）: {len(only_in_discord)} 件")
    print()
    
    if only_in_db:
        print("   🔴 DB にのみ存在するユーザー（Discord ロール削除済みか？）:")
        print(f"      Total: {len(only_in_db)}")
        for discord_id in sorted(only_in_db):
            # その行の詳細を確認
            cur.execute("""
                SELECT discord_id, assigned_by, assigned_at, created_at
                FROM member_list WHERE discord_id = %s
            """, (discord_id,))
            row = cur.fetchone()
            print(f"        - {discord_id:20s} assigned_by={row['assigned_by']}, assigned_at={row['assigned_at']}")
        print()
    
    if only_in_discord:
        print("   🟡 Discord にのみ存在するユーザー（DB に追加が必要）:")
        print(f"      Total: {len(only_in_discord)}")
        for i, user_id in enumerate(sorted(only_in_discord)[:20], 1):
            print(f"        {i:2d}. {user_id}")
        if len(only_in_discord) > 20:
            print(f"        ... and {len(only_in_discord) - 20} more")
        print()
    
    # 4. admin_list も確認
    print("📋 4. admin_list の確認")
    print("-" * 60)
    cur.execute("SELECT COUNT(*) as count FROM admin_list")
    admin_count = cur.fetchone()["count"]
    print(f"   Total admin records: {admin_count}")
    
    cur.execute("""
        SELECT discord_id FROM admin_list ORDER BY discord_id
    """)
    admin_list = [row["discord_id"] for row in cur.fetchall()]
    print(f"   Admin IDs: {', '.join(sorted(admin_list))}")
    print()
    
    # 5. pre_member_list も確認
    print("📋 5. pre_member_list の確認")
    print("-" * 60)
    cur.execute("SELECT COUNT(*) as count FROM pre_member_list")
    pre_member_count = cur.fetchone()["count"]
    print(f"   Total pre_member records: {pre_member_count}")
    print()
    
    # 6. サマリー
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"  member_list DB records:  {member_list_count}")
    print(f"  Discord member role:     {member_role_count}")
    print(f"  ✓ Synced (both):         {len(both)}")
    print(f"  ❌ DB only (mismatch):   {len(only_in_db)}")
    print(f"  ⚠️  Discord only:         {len(only_in_discord)}")
    print()
    
    if len(only_in_db) > 0:
        print(f"💡 Recommendation:")
        print(f"   Run 'sync_member_lists' API endpoint to resync from Discord")
        print(f"   or DELETE manually from DB the {len(only_in_db)} orphaned records")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
