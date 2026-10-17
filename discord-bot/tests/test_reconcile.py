"""run_reconcile のロール付与のテスト（#184）

- sub_user_list のユーザーに sub垢 ロール（SUB_USER_ROLE_IDS）を付与する
- sub_user_list にいないユーザーには sub垢 ロールを付与しない
- SUB_USER_ROLE_IDS が未設定なら sub垢 ロールは付与しない
- リストにいないユーザーからロールを外さない
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
	"member_list": [{"discord_id": "user-member"}],
	"sub_user_list": [{"discord_id": "user-sub"}],
	"pre_member_list": [{"discord_id": "user-pre"}],
}


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
		self.assertEqual(sub_role_targets, {"user-sub"})

	def test_skips_sub_user_role_when_not_configured(self):
		_, operations = _run("")

		self.assertFalse(any(role == SUB_ROLE for _, _, role in operations))
		# sub_user には従来どおり member ロールを付与する
		self.assertIn(("PUT", "user-sub", MEMBER_ROLE), operations)

	def test_removes_only_pre_member_role(self):
		_, operations = _run(SUB_ROLE)

		removed = {(user, role) for method, user, role in operations if method == "DELETE"}
		self.assertEqual(removed, {("user-member", PRE_ROLE), ("user-sub", PRE_ROLE)})


if __name__ == "__main__":
	unittest.main()
