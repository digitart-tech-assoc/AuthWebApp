class OTPTooManyAttemptsError(ValueError):
	pass


class OTPVerificationBusyError(Exception):
	"""同じ OTP の検証が並行して行われており、行ロックの待ち時間が上限を超えた"""

	def __init__(self, message: str = "同じ認証コードの確認が同時に行われています。しばらく待ってから再度お試しください。") -> None:
		super().__init__(message)


class RegistrationNotEligibleError(Exception):
	"""入会資格（pre_member かつ入会費支払済み）を満たさない"""
	pass
