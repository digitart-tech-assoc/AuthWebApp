#!/usr/bin/env python3
"""開発用: ユーザーのロールを CLI からワンコマンドで切り替える。

Usage:
    python dev_switch_role.py admin              # admin に切替
    python dev_switch_role.py member             # member に切替
    python dev_switch_role.py pre_member          # pre_member に切替
    python dev_switch_role.py pre_member --paid   # pre_member + 入会費支払済
    python dev_switch_role.py none               # 新規接触者（メンバーシップなし）
    python dev_switch_role.py obog               # OB/OG に切替

    --discord-id <ID>  : 切替対象の discord_id を指定（省略時: .envから自動検出不可のため必須）
    --paid             : paid_invitations にも追加
    --show             : 現在のロールを表示するだけ

.env から DATABASE_URL を自動で読み込みます。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# .env を読み込む (python-dotenv がない場合は手動パース)
def load_dotenv_simple(env_path: Path) -> None:
    """最低限の .env パーサー"""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# プロジェクトルートの .env を読み込む
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv_simple(PROJECT_ROOT / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("❌ DATABASE_URL が設定されていません。.env を確認してください。", file=sys.stderr)
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 がインストールされていません: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


ALLOWED_ROLES = {"admin", "member", "pre_member", "obog", "sub_user", "none"}


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def show_current_state(discord_id: str) -> None:
    """現在のロールと支払い状態を表示する。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # メンバーシップ取得
            cur.execute(
                "SELECT membership_type, assigned_at FROM user_memberships WHERE discord_id = %s ORDER BY assigned_at",
                (discord_id,)
            )
            memberships = cur.fetchall()

            # paid_invitations 確認
            cur.execute(
                "SELECT 1 FROM paid_invitations WHERE discord_id = %s AND (expires_at IS NULL OR expires_at > now())",
                (discord_id,)
            )
            is_paid = cur.fetchone() is not None

        print(f"\n📋 Discord ID: {discord_id}")
        print(f"{'─' * 40}")
        if memberships:
            for mt, at in memberships:
                print(f"  🏷️  {mt} (assigned: {at})")
        else:
            print("  ⚪ メンバーシップなし (none)")
        print(f"  💰 入会費支払い: {'✅ 済' if is_paid else '❌ 未'}")
        print()
    finally:
        conn.close()


def switch_role(discord_id: str, target_role: str, is_paid: bool) -> None:
    """ロールを切り替える。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. 全メンバーシップをクリア
            cur.execute("DELETE FROM user_memberships WHERE discord_id = %s", (discord_id,))

            # 2. paid_invitations をクリア
            cur.execute("DELETE FROM paid_invitations WHERE discord_id = %s", (discord_id,))

            # 3. 新しいメンバーシップを追加
            if target_role != "none":
                cur.execute(
                    """
                    INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
                    VALUES (%s, %s, 'dev-cli', now(), now())
                    ON CONFLICT (discord_id, membership_type) DO NOTHING
                    """,
                    (discord_id, target_role)
                )

            # 4. paid_invitations を追加
            if is_paid:
                cur.execute(
                    """
                    INSERT INTO paid_invitations (discord_id, note, assigned_by)
                    VALUES (%s, 'dev-cli', 'dev-cli')
                    ON CONFLICT (discord_id) DO UPDATE SET note = 'dev-cli', assigned_by = 'dev-cli', assigned_at = now()
                    """,
                    (discord_id,)
                )

            conn.commit()

        print(f"\n✅ ロールを切り替えました:")
        print(f"   → {target_role}{'  💰 入会費支払済' if is_paid else ''}")
        print(f"\n⚠️  ブラウザをリロードして反映してください。\n")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ エラー: {e}\n", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="開発用: ユーザーのロールをワンコマンドで切り替える",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python dev_switch_role.py admin --discord-id 123456789
  python dev_switch_role.py pre_member --paid --discord-id 123456789
  python dev_switch_role.py none --discord-id 123456789
  python dev_switch_role.py --show --discord-id 123456789
        """,
    )
    parser.add_argument(
        "role",
        nargs="?",
        choices=sorted(ALLOWED_ROLES),
        help="切替先のロール",
    )
    parser.add_argument(
        "--discord-id",
        required=True,
        help="対象ユーザーの Discord ID",
    )
    parser.add_argument(
        "--paid",
        action="store_true",
        help="paid_invitations にも追加する（入会費支払済み状態にする）",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="現在のロールを表示するだけ（切替しない）",
    )

    args = parser.parse_args()

    if args.show:
        show_current_state(args.discord_id)
        return

    if args.role is None:
        parser.error("ロールを指定してください（例: admin, member, pre_member, none）")

    print(f"🔄 ロール切替: {args.discord_id} → {args.role}{'  (+paid)' if args.paid else ''}")
    switch_role(args.discord_id, args.role, args.paid)
    show_current_state(args.discord_id)


if __name__ == "__main__":
    main()
