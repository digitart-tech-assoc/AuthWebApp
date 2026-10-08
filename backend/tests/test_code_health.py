"""非推奨 API の使用や型ヒントの import 漏れがないことのテスト（#150）"""

import inspect
import typing
import warnings

import pytest
from pydantic.warnings import PydanticDeprecatedSince20

from app.api.v1 import roles as roles_api
from app.api.v1 import survey as survey_api


@pytest.mark.asyncio
async def test_survey_payload_is_built_without_deprecated_dict(monkeypatch):
	saved_payloads = []
	monkeypatch.setattr(survey_api.repository, "get_student_profile", lambda discord_id: None)
	monkeypatch.setattr(
		survey_api.repository,
		"save_member_survey_response",
		lambda profile_id, student_number, join_request_id, payload: saved_payloads.append(payload)
		or {"id": 1, "created_at": None},
	)
	request = survey_api.SurveyRequest(digitart_channels=["公式ウェブサイト"], join_request_id="request-id")

	with warnings.catch_warnings():
		warnings.simplefilter("error", PydanticDeprecatedSince20)
		await survey_api.submit_survey(request, principal={"discord_id": "test-discord-id"})

	assert saved_payloads == [request.model_dump()]


def test_roles_module_type_hints_are_resolvable():
	# from __future__ import annotations のため、import 漏れは注釈を評価したときに初めて NameError になる
	for name, func in inspect.getmembers(roles_api, inspect.isfunction):
		if func.__module__ == roles_api.__name__:
			typing.get_type_hints(func)
