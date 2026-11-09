class OTPTooManyAttemptsError(ValueError):
	pass


class OTPVerificationBusyError(Exception):
	"""同じ OTP の検証が並行して行われており、行ロックの待ち時間が上限を超えた"""

	def __init__(self, message: str = "同じ認証コードの確認が同時に行われています。しばらく待ってから再度お試しください。") -> None:
		super().__init__(message)


class RegistrationNotEligibleError(Exception):
	"""入会資格（pre_member かつ入会費支払済み）を満たさない"""
	pass


class MembershipAssignmentError(ValueError):
	"""管理画面の割当の保存で、会員種別として成り立たない状態になる（#251）

	レスポンスの detail には response_detail（固定文言に Discord ID と種別名を埋めたもの）を使う。
	"""

	PARTIAL = "partial"
	EXCLUSIVE = "exclusive"

	def __init__(self, reason: str, discord_id: str, membership_types: tuple[str, ...]) -> None:
		self.reason = reason
		self.discord_id = discord_id
		self.membership_types = membership_types
		super().__init__(self.response_detail)

	@property
	def response_detail(self) -> str:
		names = " と ".join(f"'{t}'" for t in self.membership_types)
		if self.reason == self.PARTIAL:
			return f"{self.discord_id}: 会員種別 {names} のロールは、すべて付けるか、すべて外してください"
		return f"{self.discord_id}: 会員種別 {names} のロールを同時に付けることはできません"
