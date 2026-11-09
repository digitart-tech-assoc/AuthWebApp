"""run_reconcile のロール付与のテスト（#184）

- sub_user_list のユーザーに sub垢 ロール（SUB_USER_ROLE_IDS）を付与する
- sub_user_list にいないユーザーには sub垢 ロールを付与しない
- SUB_USER_ROLE_IDS が未設定なら sub垢 ロールは付与しない
- リストにいないユーザーからロールを外さない
- sub_user_list のユーザーには member ロールを付与しない（#251）
"""

import asyncio
import unittest
from unittest import mock

import httpx

from app.services import reconcile

GUILD_ID = "guild"
MEMBER_ROLE = "role-member"
PRE_ROLE = "role-pre"
SUB_ROLE = "role-sub"

LISTS = {
	"member_list": [{"discord_id": "user-member"}, {"discord_id": "user-both"}],
	"sub_user_list": [{"discord_id": "user-sub"}, {"discord_id": "user-both"}],
	# user-sub-pre は sub_user と pre_member の両方の行を持つ（pre-member ロールは付けない）
	"pre_member_list": [{"discord_id": "user-pre"}, {"discord_id": "user-sub-pre"}],
}
LISTS["sub_user_list"].append({"discord_id": "user-sub-pre"})


def _run(sub_user_role_ids: str) -> tuple[dict, list[tuple[str, str, str]]]:
	"""Backend と Discord を MockTransport で置き換えて run_reconcile を実行し、(結果, ロール操作の一覧) を返す。"""
	operations: list[tuple[str, str, str]] = []

	def handler(request: httpx.Request) -> httpx.Response:
		if request.url.path == "/api/v1/members/internal/lists":
			return httpx.Response(200, json={"data": LISTS})
		# /api/v10/guilds/{guild_id}/members/{user_id}/roles/{role_id}
		parts = request.url.path.split("/")
		operations.append((request.method, parts[-3], parts[-1]))
		return httpx.Response(204)

	transport = httpx.MockTransport(handler)
	real_client = httpx.AsyncClient

	with mock.patch.multiple(
		reconcile,
		BACKEND_URL="http://backend",
		SHARED_SECRET="secret",
		DISCORD_TOKEN="token",
		DISCORD_GUILD_ID=GUILD_ID,
		PRE_MEMBER_ROLE_ID=PRE_ROLE,
		MEMBER_ROLE_IDS=MEMBER_ROLE,
		SUB_USER_ROLE_IDS=sub_user_role_ids,
	), mock.patch.object(
		reconcile.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs)
	):
		result = asyncio.run(reconcile.run_reconcile())

	return result, operations


class RunReconcileSubUserRoleTest(unittest.TestCase):
	def test_adds_sub_user_role_to_sub_users(self):
		result, operations = _run(SUB_ROLE)

		self.assertTrue(result["ok"])
		self.assertIn(("PUT", "user-sub", SUB_ROLE), operations)

	def test_does_not_add_sub_user_role_to_others(self):
		_, operations = _run(SUB_ROLE)

		sub_role_targets = {user for method, user, role in operations if role == SUB_ROLE}
		self.assertEqual(sub_role_targets, {"user-sub", "user-both", "user-sub-pre"})

	def test_skips_sub_user_role_when_not_configured(self):
		_, operations = _run("")

		self.assertFalse(any(role == SUB_ROLE for _, _, role in operations))

	def test_adds_member_role_only_to_members(self):
		# sub_user に member ロールを付けると、管理画面で外しても push のたびに戻るため付けない（#251）
		_, operations = _run(SUB_ROLE)

		member_role_targets = {user for method, user, role in operations if role == MEMBER_ROLE}
		# member と sub_user の両方の行がある人（user-both）にも付けない
		self.assertEqual(member_role_targets, {"user-member"})

	def test_does_not_add_pre_member_role_to_members_or_sub_users(self):
		_, operations = _run(SUB_ROLE)

		added_pre = {user for method, user, role in operations if method == "PUT" and role == PRE_ROLE}
		self.assertEqual(added_pre, {"user-pre"})

	def test_removes_only_pre_member_role(self):
		_, operations = _run(SUB_ROLE)

		removed = {(user, role) for method, user, role in operations if method == "DELETE"}
		self.assertEqual(removed, {(u, PRE_ROLE) for u in ("user-member", "user-sub", "user-both", "user-sub-pre")})


if __name__ == "__main__":
	unittest.main()
