"""役割: 会員種別（user_memberships）とロールの割当の既存データを整理する（#251 段階 4）

整理の内容は app/db/membership_backfill.py を参照。既定では件数を表示するだけで、何も書き込まない。

使い方（Backend のコンテナ内で実行する。DATABASE_URL と会員種別のロール ID の環境変数が必要）:
	python -m app.scripts.fix_membership_assignments           # 件数の確認だけ（dry-run）
	python -m app.scripts.fix_membership_assignments --apply   # 反映する（監査ログに記録する）

反映したあと、管理画面から push すると Discord のロールにも反映される。
出力するのは件数だけで、Discord ID などは出さない。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from app.core.membership_roles import REQUIRED_MEMBERSHIP_TYPES, missing_membership_role_id_env_vars
from app.db.audit_repository import OP_MEMBERSHIP_BACKFILL, AuditContext
from app.db.connection import _connect
from app.db.membership_backfill import run_backfill

ACTOR_SUB = "maintenance-script"


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="user_memberships と role_member_assignments の食い違いを整理する（#251）")
	parser.add_argument("--apply", action="store_true", help="変更を反映する（指定しなければ件数の確認だけ）")
	args = parser.parse_args(argv)

	missing = missing_membership_role_id_env_vars(REQUIRED_MEMBERSHIP_TYPES)
	if missing:
		print(f"Required membership role IDs are not set: {', '.join(missing)}", file=sys.stderr)
		return 1

	# 任意の種別（sub_user / obog）が未設定だと、その種別は整理の対象にならない。出力に含めて見落としを防ぐ
	unconfigured = missing_membership_role_id_env_vars()
	request_id = str(uuid.uuid4())
	audit = AuditContext(request_id, ACTOR_SUB, None, OP_MEMBERSHIP_BACKFILL) if args.apply else None
	with _connect() as conn:
		plan = run_backfill(conn, apply=args.apply, audit=audit)

	print(json.dumps({
		"mode": "apply" if args.apply else "dry-run",
		"request_id": request_id if args.apply else None,
		"unconfigured_role_id_env_vars": unconfigured,
		**plan.summary(),
	}, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	sys.exit(main())
