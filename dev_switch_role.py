#!/usr/bin/env python3
"""開発用: ユーザーのロールを CLI からワンコマンドで切り替える。

ペルソナ:
    admin           : 管理者権限
    member          : 正会員
    pre_member      : 新規・Discord参加者（未払い）
    pre_member+paid : Discord参加済み・入会費支払い完了者
    none            : 新規接触者（メンバーシップなし・未払い）
    obog            : 卒業生メンバー（OB/OG）
    sub_user        : サブユーザー

Usage:
    python dev_switch_role.py admin
    python dev_switch_role.py member
    python dev_switch_role.py pre_member
    python dev_switch_role.py pre_member+paid
    python dev_switch_role.py none
    python dev_switch_role.py obog
    python dev_switch_role.py sub_user

    # オプション:
    python dev_switch_role.py --show                      # 現在の状態を表示
    python dev_switch_role.py admin --discord-id <ID>     # 特定のDiscord IDを指定
    python dev_switch_role.py pre_member --paid           # --paid フラグ併用も可能

.env から DATABASE_URL を自動で読み込みます。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Windows コンソールでの UTF-8 / 絵文字出力対応
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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


# 対象ペルソナ定義
PERSONAS = {
    "admin": {"role": "admin", "is_paid": False, "desc": "管理者権限（全機能・全管理画面アクセス可）"},
    "member": {"role": "member", "is_paid": False, "desc": "正会員（通常会員権限）"},
    "pre_member": {"role": "pre_member", "is_paid": False, "desc": "Discord参加済み・入会費未払い"},
    "pre_member+paid": {"role": "pre_member", "is_paid": True, "desc": "Discord参加済み・入会費支払い完了者"},
    "none": {"role": "none", "is_paid": False, "desc": "新規接触者（メンバーシップなし）"},
    "obog": {"role": "obog", "is_paid": False, "desc": "卒業生メンバー（OB/OG）"},
    "sub_user": {"role": "sub_user", "is_paid": False, "desc": "サブユーザー（サブアカウント等）"},
}


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def find_candidates() -> list[dict]:
    """DBから候補となるユーザー（discord_id, 表示名等）を検索する。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # users テーブルまたは user_memberships / guild_members から探索
            candidates = []
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('users', 'user_memberships', 'guild_members');
            """)
            tables = {row[0] for row in cur.fetchall()}

            if "users" in tables:
                cur.execute("""
                    SELECT u.discord_id, u.display_name, u.email, u.app_role 
                    FROM users u
                    WHERE u.discord_id IS NOT NULL AND u.discord_id != ''
                    ORDER BY u.created_at DESC LIMIT 10
                """)
                for row in cur.fetchall():
                    candidates.append({
                        "discord_id": row[0],
                        "name": row[1] or row[2] or "不明",
                        "current_role": row[3] or "none"
                    })
            elif "user_memberships" in tables:
                cur.execute("""
                    SELECT DISTINCT discord_id FROM user_memberships LIMIT 10
                """)
                for row in cur.fetchall():
                    candidates.append({
                        "discord_id": row[0],
                        "name": row[0],
                        "current_role": "unknown"
                    })
            return candidates
    except Exception as e:
        print(f"⚠️ ユーザー候補の検索中にエラーが発生しました: {e}", file=sys.stderr)
        return []
    finally:
        conn.close()


def resolve_discord_id(specified_id: str | None) -> str:
    """discord_id を決定する。未指定なら自動検出または対話式選択。"""
    if specified_id:
        return specified_id.strip()

    candidates = find_candidates()
    if not candidates:
        print("❌ 対象の Discord ID を自動特定できませんでした。--discord-id <ID> を指定してください。", file=sys.stderr)
        sys.exit(1)

    if len(candidates) == 1:
        auto_id = candidates[0]["discord_id"]
        print(f"ℹ️  対象ユーザーを自動選択しました: {candidates[0]['name']} (Discord ID: {auto_id})")
        return auto_id

    print("\n🔍 複数のユーザーが見つかりました。対象を選択してください:")
    for i, c in enumerate(candidates, 1):
        print(f"  [{i}] {c['name']} (ID: {c['discord_id']}, Role: {c['current_role']})")

    try:
        choice = input("\n番号を入力してください (1-{}): ".format(len(candidates))).strip()
        idx = int(choice) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx]["discord_id"]
        else:
            print("無効な選択です。", file=sys.stderr)
            sys.exit(1)
    except (ValueError, EOFError, KeyboardInterrupt):
        print("\n中断されました。--discord-id <ID> を指定して再実行してください。", file=sys.stderr)
        sys.exit(1)


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

        # ペルソナ判定
        current_persona = "none"
        if memberships:
            m_types = [m[0] for m in memberships]
            if "admin" in m_types:
                current_persona = "admin"
            elif "member" in m_types:
                current_persona = "member"
            elif "sub_user" in m_types:
                current_persona = "sub_user"
            elif "pre_member" in m_types:
                current_persona = "pre_member+paid" if is_paid else "pre_member"
            elif "obog" in m_types:
                current_persona = "obog"

        print(f"\n📋 Discord ID: {discord_id}")
        print(f"{'─' * 45}")
        print(f"  🎭 検出ペルソナ: 【 {current_persona} 】")
        if memberships:
            for mt, at in memberships:
                print(f"     🏷️  user_memberships: {mt} (assigned: {at})")
        else:
            print("     ⚪ user_memberships: なし (none)")
        print(f"  💰 paid_invitations: {'✅ 登録あり (支払い済み)' if is_paid else '❌ 未登録'}")
        print(f"{'─' * 45}\n")
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

        print(f"✨ ロール切替完了:")
        print(f"   → ロール: {target_role}{'  💰 (入会費支払済)' if is_paid else ''}")
        print(f"   ⚠️  ブラウザをリロードして反映を確認してください。")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ エラーが発生しました: {e}\n", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="開発用: ユーザーのペルソナ・ロールをワンコマンドで切り替える",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
指定可能なペルソナ (7種):
  admin           : 管理者権限（全機能・全管理画面アクセス可）
  member          : 正会員（通常会員権限）
  pre_member      : Discord参加済み・入会費未払い
  pre_member+paid : Discord参加済み・入会費支払い完了者
  none            : 新規接触者（メンバーシップなし）
  obog            : 卒業生メンバー（OB/OG）
  sub_user        : サブユーザー（サブアカウント等）

使用例:
  python dev_switch_role.py admin
  python dev_switch_role.py member
  python dev_switch_role.py pre_member
  python dev_switch_role.py pre_member+paid
  python dev_switch_role.py none
  python dev_switch_role.py obog
  python dev_switch_role.py sub_user
  python dev_switch_role.py --show
        """,
    )
    parser.add_argument(
        "persona",
        nargs="?",
        choices=list(PERSONAS.keys()),
        help="切替対象のペルソナ (admin, member, pre_member, pre_member+paid, none, obog, sub_user)",
    )
    parser.add_argument(
        "--discord-id",
        help="対象ユーザーの Discord ID（省略時は自動検出または選択）",
    )
    parser.add_argument(
        "--paid",
        action="store_true",
        help="paid_invitations にも追加する（pre_member 以外のロールでも明示的に付与可能）",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="現在のペルソナ・ロールを表示するだけ（切替なし）",
    )

    args = parser.parse_args()

    # Discord ID の解決
    discord_id = resolve_discord_id(args.discord_id)

    if args.show:
        show_current_state(discord_id)
        return

    if args.persona is None:
        parser.error("ペルソナを指定してください（例: admin, member, pre_member, pre_member+paid, none, obog, sub_user）")

    config = PERSONAS[args.persona]
    target_role = config["role"]
    is_paid = config["is_paid"] or args.paid

    print(f"\n🔄 ペルソナ切替を実行中...")
    print(f"   対象 ID : {discord_id}")
    print(f"   ペルソナ: {args.persona} ({config['desc']})")
    print(f"{'─' * 45}")

    switch_role(discord_id, target_role, is_paid)
    show_current_state(discord_id)


if __name__ == "__main__":
    main()
