"""SHARED_SECRET の検証と内部認証のテスト（#80）

- 本番（BOT_ENV=production）では SHARED_SECRET が未設定または16文字未満なら起動しない
- 本番以外では警告のみで起動する
- メッセージに SHARED_SECRET の値を含めない
- SHARED_SECRET が未設定なら、どのトークンでも内部 API を通さない
"""

import asyncio
import unittest
from unittest import mock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import main, shared_secret
from app.web import internal_api

STRONG_SECRET = "s" * shared_secret.MIN_SHARED_SECRET_LENGTH
SHORT_SECRET = "s" * (shared_secret.MIN_SHARED_SECRET_LENGTH - 1)


class ValidateSharedSecretTest(unittest.TestCase):
	def test_production_rejects_weak_secret(self) -> None:
		for value in ("", SHORT_SECRET):
			with self.subTest(value=value), mock.patch.object(shared_secret, "SHARED_SECRET", value):
				with self.assertRaises(RuntimeError) as cm:
					shared_secret.validate_shared_secret("production")
				if value:
					self.assertNotIn(value, str(cm.exception))

	def test_production_accepts_secret_of_minimum_length(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", STRONG_SECRET):
			shared_secret.validate_shared_secret("production")

	def test_non_production_only_warns(self) -> None:
		for env in ("development", ""):
			for value in ("", SHORT_SECRET):
				with self.subTest(env=env, value=value), mock.patch.object(shared_secret, "SHARED_SECRET", value):
					with self.assertLogs(shared_secret.logger, level="WARNING") as cm:
						shared_secret.validate_shared_secret(env)
					output = "\n".join(cm.output)
					self.assertIn("SHARED_SECRET", output)
					if value:
						self.assertNotIn(value, output)

	def test_non_production_does_not_warn_for_strong_secret(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", STRONG_SECRET):
			with self.assertNoLogs(shared_secret.logger, level="WARNING"):
				shared_secret.validate_shared_secret("development")

	def test_main_stops_before_starting_in_production_with_weak_secret(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", SHORT_SECRET), \
			mock.patch.object(main, "BOT_ENV", "production"), \
			mock.patch.object(main, "run_web_api", mock.AsyncMock()) as run_web_api, \
			mock.patch.object(main, "run_bot_if_configured", mock.AsyncMock()) as run_bot:
			with self.assertRaises(RuntimeError):
				asyncio.run(main.main())
		run_web_api.assert_not_called()
		run_bot.assert_not_called()


class InternalTokenTest(unittest.TestCase):
	def test_unset_secret_never_matches(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", ""):
			for token in (None, "", " ", "anything"):
				with self.subTest(token=token):
					self.assertFalse(shared_secret.is_internal_token(token))

	def test_matching_token(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", STRONG_SECRET):
			self.assertTrue(shared_secret.is_internal_token(STRONG_SECRET))
			self.assertFalse(shared_secret.is_internal_token(STRONG_SECRET + "x"))
			# 非 ASCII のトークンでも例外にならず不一致となる
			self.assertFalse(shared_secret.is_internal_token("ひみつ"))

	def test_verify_internal_authorization(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", STRONG_SECRET):
			shared_secret.verify_internal_authorization(f"Bearer {STRONG_SECRET}")
			for authorization in (None, "", "Bearer", "Bearer ", f"Basic {STRONG_SECRET}", "Bearer wrong"):
				with self.subTest(authorization=authorization):
					with self.assertRaises(HTTPException) as cm:
						shared_secret.verify_internal_authorization(authorization)
					self.assertEqual(cm.exception.status_code, 401)


class InternalSyncEndpointTest(unittest.TestCase):
	def setUp(self) -> None:
		app = FastAPI()
		app.include_router(internal_api.router)
		self.client = TestClient(app)

	def test_rejects_when_secret_unset(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", ""), \
			mock.patch.object(internal_api, "run_reconcile", mock.AsyncMock()) as run_reconcile:
			for headers in ({}, {"Authorization": "Bearer "}):
				with self.subTest(headers=headers):
					res = self.client.post("/internal/sync", json={}, headers=headers)
					self.assertEqual(res.status_code, 401)
		run_reconcile.assert_not_called()

	def test_accepts_matching_secret(self) -> None:
		with mock.patch.object(shared_secret, "SHARED_SECRET", STRONG_SECRET), \
			mock.patch.object(internal_api, "run_reconcile", mock.AsyncMock(return_value={"ok": True})):
			res = self.client.post("/internal/sync", json={}, headers={"Authorization": f"Bearer {STRONG_SECRET}"})
		self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
	unittest.main()
