"""学生プロフィールの学部学科（Frontend の「その他（手入力）」による自由入力）の検証テスト"""

import pytest
from pydantic import ValidationError

from app.api.v1 import student as student_api


def _profile_request(department: str) -> student_api.StudentProfileRequest:
	return student_api.StudentProfileRequest(
		student_number="1A234567",
		name="テスト 太郎",
		furigana="テスト タロウ",
		department=department,
		gender=None,
		phone="09000000000",
	)


@pytest.mark.parametrize("department", ["テスト学部テスト学科", "あ" * 100])
def test_department_accepts_free_text_not_in_options(department):
	assert _profile_request(department).department == department


@pytest.mark.parametrize("department", ["", "あ" * 101])
def test_department_rejects_empty_or_too_long(department):
	with pytest.raises(ValidationError):
		_profile_request(department)
