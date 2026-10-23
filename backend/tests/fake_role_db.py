"""ロール関連テーブル（role_categories / role_manifests / role_member_assignments / role_audit_logs）の
インメモリの代替。リポジトリ関数が発行する SQL だけを解釈する。

_connect() の代わりに使い、with を抜けるときに _PooledConnection と同じく、正常終了なら commit、例外なら rollback する。
"""

from __future__ import annotations

import copy
import json
from typing import Any

CATEGORY_COLUMNS = ("id", "name", "display_order", "is_collapsed", "permissions", "is_restricted")
ROLE_COLUMNS = ("role_id", "name", "color", "hoist", "mentionable", "permissions", "position", "category_id", "is_our_bot")
AUDIT_COLUMNS = (
	"request_id", "operation", "system", "target_type", "target_id", "action",
	"before", "after", "actor_sub", "actor_discord_id",
)


class AuditInsertError(Exception):
	"""role_audit_logs への INSERT を失敗させるときに送出する例外。"""


class FakeRoleDB:
	def __init__(self):
		self.categories: dict[str, dict[str, Any]] = {}
		self.roles: dict[str, dict[str, Any]] = {}
		self.assignments: set[tuple[str, str]] = set()
		self.audit_logs: list[dict[str, Any]] = []
		self.executed: list[str] = []
		self.fail_audit_insert = False
		self.commits = 0
		self.rollbacks = 0

	# --- 初期データ ---
	def add_category(self, id: str, name: str = "cat", **kwargs: Any) -> None:
		row = {"id": id, "name": name, "display_order": 0, "is_collapsed": False, "permissions": 0, "is_restricted": False}
		row.update(kwargs)
		self.categories[id] = row

	def add_role(self, role_id: str, name: str = "role", **kwargs: Any) -> None:
		row = {
			"role_id": role_id, "name": name, "color": "#000000", "hoist": False, "mentionable": False,
			"permissions": 0, "position": 1, "category_id": None, "is_our_bot": False,
		}
		row.update(kwargs)
		self.roles[role_id] = row

	def assign(self, role_id: str, *user_ids: str) -> None:
		for user_id in user_ids:
			self.assignments.add((role_id, user_id))

	def members_of(self, role_id: str) -> set[str]:
		return {u for r, u in self.assignments if r == role_id}

	def connect(self) -> "FakeConnection":
		return FakeConnection(self)

	def writes(self) -> list[str]:
		return [sql for sql in self.executed if not sql.startswith("SELECT")]

	def _state(self):
		return (copy.deepcopy(self.categories), copy.deepcopy(self.roles), set(self.assignments), list(self.audit_logs))

	def _restore(self, state) -> None:
		self.categories, self.roles, self.assignments, self.audit_logs = state


class FakeConnection:
	def __init__(self, db: FakeRoleDB):
		self.db = db
		self._saved = db._state()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		if exc_type is None:
			self.commit()
		else:
			self.rollback()
		return False

	def cursor(self):
		return FakeCursor(self.db)

	def commit(self):
		self.db.commits += 1
		self._saved = self.db._state()

	def rollback(self):
		self.db.rollbacks += 1
		self.db._restore(self._saved)

	def close(self):
		pass


class FakeCursor:
	def __init__(self, db: FakeRoleDB):
		self.db = db
		self.rowcount = 0
		self._rows: list[tuple] = []

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def fetchall(self):
		return list(self._rows)

	def fetchone(self):
		return self._rows[0] if self._rows else None

	def execute(self, sql: str, params: tuple | None = None) -> None:
		db = self.db
		q = " ".join(sql.split())
		db.executed.append(q)
		params = params or ()
		self._rows = []
		self.rowcount = 0

		if q.startswith("SELECT user_id FROM role_member_assignments WHERE role_id = %s"):
			self._rows = [(u,) for u in sorted(db.members_of(params[0]))]
		elif q.startswith("SELECT role_id FROM role_member_assignments WHERE user_id = %s"):
			self._rows = [(r,) for r, u in sorted(db.assignments) if u == params[0]]
		elif q.startswith("SELECT role_id, user_id FROM role_member_assignments WHERE role_id = %s"):
			self._rows = [(r, u) for r, u in sorted(db.assignments) if r == params[0]]
		elif q.startswith("SELECT " + ", ".join(CATEGORY_COLUMNS) + " FROM role_categories"):
			self._rows = [tuple(row[c] for c in CATEGORY_COLUMNS) for row in self._filter(db.categories, "id", q, params)]
		elif q.startswith("SELECT " + ", ".join(ROLE_COLUMNS) + " FROM role_manifests"):
			self._rows = [tuple(row[c] for c in ROLE_COLUMNS) for row in self._filter(db.roles, "role_id", q, params)]
		elif q.startswith("DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s"):
			key = (params[0], params[1])
			if key in db.assignments:
				db.assignments.discard(key)
				self.rowcount = 1
		elif q.startswith("INSERT INTO role_member_assignments"):
			key = (params[0], params[1])
			if key not in db.assignments:
				db.assignments.add(key)
				self.rowcount = 1
		elif q.startswith("DELETE FROM role_manifests WHERE role_id = ANY(%s)"):
			targets = [rid for rid in db.roles if rid in params[0]]
			self._delete_roles(targets)
		elif q.startswith("DELETE FROM role_manifests WHERE role_id <> ALL(%s)"):
			targets = [rid for rid in db.roles if rid not in params[0]]
			self._delete_roles(targets)
		elif q.startswith("DELETE FROM role_categories WHERE id = ANY(%s)"):
			self._delete_categories([cid for cid in db.categories if cid in params[0]])
		elif q.startswith("DELETE FROM role_categories WHERE id <> ALL(%s)"):
			self._delete_categories([cid for cid in db.categories if cid not in params[0]])
		elif q.startswith("INSERT INTO role_categories"):
			row = dict(zip(CATEGORY_COLUMNS, params))
			db.categories[row["id"]] = row
			self.rowcount = 1
		elif q.startswith("INSERT INTO role_manifests"):
			row = dict(zip(ROLE_COLUMNS, params))
			if row["category_id"] is not None and row["category_id"] not in db.categories:
				raise AssertionError(f"foreign key violation: {row['category_id']}")
			db.roles[row["role_id"]] = row
			self.rowcount = 1
		elif q.startswith("UPDATE role_manifests SET role_id = %s WHERE role_id = %s"):
			new_id, old_id = params
			if old_id in db.roles:
				row = db.roles.pop(old_id)
				row["role_id"] = new_id
				db.roles[new_id] = row
				self.rowcount = 1
		elif q.startswith("UPDATE role_member_assignments SET role_id = %s WHERE role_id = %s"):
			new_id, old_id = params
			moved = {(r, u) for r, u in db.assignments if r == old_id}
			db.assignments -= moved
			db.assignments |= {(new_id, u) for _, u in moved}
			self.rowcount = len(moved)
		elif q.startswith("INSERT INTO role_audit_logs"):
			if db.fail_audit_insert:
				raise AuditInsertError("audit insert failed")
			row = dict(zip(AUDIT_COLUMNS, params))
			row["before"] = json.loads(row["before"]) if row["before"] is not None else None
			row["after"] = json.loads(row["after"]) if row["after"] is not None else None
			db.audit_logs.append(row)
			self.rowcount = 1
		elif q.startswith("SELECT pg_advisory_xact_lock"):
			pass
		else:
			raise AssertionError(f"unexpected SQL: {q}")

	def _filter(self, table: dict[str, dict[str, Any]], key: str, q: str, params: tuple) -> list[dict[str, Any]]:
		"""WHERE <key> = ANY(%s) [OR category_id = ANY(%s)] / WHERE なし（全件）に対応する。"""
		rows = [dict(row) for _, row in sorted(table.items())]
		if "WHERE" not in q:
			return rows
		ids = set(params[0])
		extra = set(params[1]) if "OR category_id = ANY(%s)" in q else set()
		return [row for row in rows if row[key] in ids or (extra and row.get("category_id") in extra)]

	def _delete_roles(self, targets: list[str]) -> None:
		for rid in targets:
			del self.db.roles[rid]
		self.rowcount = len(targets)

	def _delete_categories(self, targets: list[str]) -> None:
		for cid in targets:
			del self.db.categories[cid]
			# role_manifests.category_id は ON DELETE SET NULL
			for row in self.db.roles.values():
				if row["category_id"] == cid:
					row["category_id"] = None
		self.rowcount = len(targets)
