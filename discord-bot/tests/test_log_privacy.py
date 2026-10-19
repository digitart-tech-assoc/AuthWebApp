"""Bot のログに個人情報を出さないことのテスト（#215）

- サーバー参加時のログに、ユーザー名・表示名を出さない（Discord ID は出してよい。docs/logging-and-errors.md）
"""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from app import main

GUILD_ID = "100000000000000001"
PRE_ROLE_ID = "200000000000000002"
MEMBER_ID = 300000000000000003
USERNAME = "test-username"
DISPLAY_NAME = "テスト表示名"


class _FakeMember:
	def __init__(self) -> None:
		self.id = MEMBER_ID
		self.name = USERNAME
		self.display_name = DISPLAY_NAME
		self.guild = SimpleNamespace(id=int(GUILD_ID), get_role=lambda role_id: SimpleNamespace(id=role_id))
		self.add_roles = mock.AsyncMock()

	def __str__(self) -> str:
		return USERNAME


class OnMemberJoinLogTest(unittest.TestCase):
	def test_member_join_log_has_discord_id_but_not_username(self) -> None:
		member = _FakeMember()
		with mock.patch.object(main, "DISCORD_GUILD_ID", GUILD_ID), \
			mock.patch.object(main, "PRE_MEMBER_ROLE_ID", PRE_ROLE_ID), \
			mock.patch.object(main, "_register_pre_member", mock.AsyncMock()), \
			self.assertLogs(main.logger, level="INFO") as logs:
			asyncio.run(main.on_member_join(member))

		output = "\n".join(logs.output)
		member.add_roles.assert_awaited_once()
		self.assertIn(str(MEMBER_ID), output)
		self.assertNotIn(USERNAME, output)
		self.assertNotIn(DISPLAY_NAME, output)


if __name__ == "__main__":
	unittest.main()
