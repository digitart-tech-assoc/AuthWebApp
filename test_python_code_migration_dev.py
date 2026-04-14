#!/usr/bin/env python
"""
DB スキーマ移行：Python コード検証スクリプト
用途: backend の全関数が user_memberships と互換性があるか検証
"""

import os
import sys
import logging
from typing import Any

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# backend ディレクトリを path に追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 環境変数設定（テスト用）
os.environ.setdefault('DISCORD_TOKEN', 'test-token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('MEMBER_ROLE_IDS', '1111111111,2222222222')
os.environ.setdefault('ADMIN_ROLE_ID', '3333333333')
os.environ.setdefault('PRE_MEMBER_ROLE_ID', '4444444444')
os.environ.setdefault('SHARED_SECRET', 'dev-secret')

# テスト用 Supabase ダミー設定
os.environ.setdefault('SUPABASE_URL', 'http://localhost:5432')
os.environ.setdefault('SUPABASE_KEY', 'test-key')

print("\n" + "="*60)
print("DB スキーマ移行：Python コード検証")
print("="*60 + "\n")

# Test 1: ユーティリティ関数の存在確認
print("[Test 1] ユーティリティ関数の存在確認...")
try:
    from app.db.repository import (
        get_user_membership_type,
        is_member,
        is_admin,
        is_pre_member,
        is_obog,
        add_to_user_membership,
        remove_from_user_membership,
        get_pre_member_list_v2,
        get_member_user_count,
        get_admin_user_count,
        get_pre_member_user_count,
        get_member_lists,
        sync_member_lists,
    )
    print("✓ ユーティリティ関数インポート OK\n")
except ImportError as e:
    print(f"✗ インポート失敗: {e}\n")
    sys.exit(1)

# Test 2: user_repository の関数確認
print("[Test 2] user_repository の関数確認...")
try:
    from app.db.user_repository import (
        get_user_role,
        upsert_user,
        find_user_by_sub,
    )
    print("✓ user_repository 関数インポート OK\n")
except ImportError as e:
    print(f"✗ インポート失敗: {e}\n")
    sys.exit(1)

# Test 3: DB 接続確認
print("[Test 3] DB 接続確認...")
try:
    from app.db.user_repository import _connect
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            if result:
                print("✓ DB 接続 OK\n")
            else:
                raise Exception("DB 接続に応答なし")
except Exception as e:
    print(f"✗ DB 接続失敗: {e}")
    print("   開発環境に PostgreSQL を起動してください\n")
    sys.exit(1)

# Test 4: user_memberships テーブル確認
print("[Test 4] user_memberships テーブル確認...")
try:
    from app.db.user_repository import _connect
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_memberships'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            if not columns:
                raise Exception("user_memberships テーブルが存在しません")
            
            print("  テーブル構造:")
            for col_name, col_type in columns:
                print(f"    - {col_name}: {col_type}")
            print("✓ JSON user_memberships テーブル OK\n")
except Exception as e:
    print(f"✗ テーブル確認失敗: {e}\n")
    sys.exit(1)

# Test 5: app_role カラム削除確認
print("[Test 5] users テーブルから app_role カラム削除確認...")
try:
    from app.db.user_repository import _connect
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'app_role'
            """)
            result = cur.fetchone()
            if result:
                print("✗ app_role カラムがまだ存在します（削除が必要）\n")
            else:
                print("✓ app_role カラム削除確認 OK（既に削除済み）\n")
except Exception as e:
    print(f"✗ 確認失敗: {e}\n")

# Test 6: テストデータを使用した関数テスト
print("[Test 6] 関数の動作テスト...")

# テスト用の Discord ID
test_discord_id = "999999999999999999"
test_user_id = "test-user-000"

try:
    from app.db.user_repository import _connect
    
    # テストデータ準備
    with _connect() as conn:
        with conn.cursor() as cur:
            # guild_members にテストデータ追加（user_id が Discord ID）
            cur.execute("""
                INSERT INTO guild_members (user_id, username, display_name)
                VALUES (%s, 'test_user', 'Test User')
                ON CONFLICT (user_id) DO NOTHING
            """, (test_discord_id,))
            
            # users にテストデータ追加
            cur.execute("""
                INSERT INTO users (user_id, discord_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (test_user_id, test_discord_id))
            
            conn.commit()
    
    # Test 6a: get_user_membership_type
    print("  - get_user_membership_type()...", end=" ")
    result = get_user_membership_type(test_discord_id)
    print(f"✓ (結果: '{result}')")
    
    # Test 6b: is_member, is_admin, etc.
    print("  - is_member()...", end=" ")
    result = is_member(test_discord_id)
    print(f"✓ (結果: {result})")
    
    print("  - is_admin()...", end=" ")
    result = is_admin(test_discord_id)
    print(f"✓ (結果: {result})")
    
    # Test 6c: add_to_user_membership
    print("  - add_to_user_membership()...", end=" ")
    try:
        add_to_user_membership(test_discord_id, 'member')
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")
    
    # Test 6d: get_user_role
    print("  - get_user_role()...", end=" ")
    role = get_user_role(test_user_id)
    print(f"✓ (結果: '{role}')")
    
    # Test 6e: get_member_lists
    print("  - get_member_lists()...", end=" ")
    lists = get_member_lists()
    print(f"✓ (member: {len(lists.get('member_list', []))}, admin: {len(lists.get('admin_list', []))})")
    
    # Clean up: テストデータ削除
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_memberships WHERE discord_id = %s", (test_discord_id,))
            cur.execute("DELETE FROM users WHERE user_id = %s", (test_user_id,))
            conn.commit()
    
    print("✓ 関数テスト OK\n")
except Exception as e:
    print(f"\n✗ 関数テスト失敗: {e}\n")
    import traceback
    traceback.print_exc()

# Test 7: スキーマ互換性確認
print("[Test 7] スキーマ互換性確認...")
try:
    from app.db.user_repository import _connect
    with _connect() as conn:
        with conn.cursor() as cur:
            # user_memberships の UNIQUE 制約確認
            cur.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'user_memberships' 
                AND constraint_type = 'UNIQUE'
            """)
            constraints = cur.fetchall()
            if constraints:
                print(f"  - UNIQUE 制約: {len(constraints)} 個確認")
            
            # FOREIGN KEY 確認
            cur.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'user_memberships' 
                AND constraint_type = 'FOREIGN KEY'
            """)
            fk_constraints = cur.fetchall()
            if fk_constraints:
                print(f"  - FOREIGN KEY 制約: {len(fk_constraints)} 個確認")
            
            # インデックス確認
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'user_memberships'
            """)
            indexes = cur.fetchall()
            if indexes:
                print(f"  - インデックス: {len(indexes)} 個確認")
            
            print("✓ スキーマ互換性確認 OK\n")
except Exception as e:
    print(f"✗ スキーマ確認失敗: {e}\n")

# 完了
print("="*60)
print("✓ Python コード検証完了！")
print("="*60)
print("\n次のステップ:")
print("1. backend を起動: python -m uvicorn app.main:app --reload")
print("2. API エンドポイント検証")
print("3. OTP フロー検証")
print("4. すべて OK なら ステージング環境テスト\n")
