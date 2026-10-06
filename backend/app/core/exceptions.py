class OTPTooManyAttemptsError(ValueError):
	pass


class OTPVerificationBusyError(Exception):
	"""同じ OTP の検証が並行して行われており、行ロックの待ち時間が上限を超えた"""
	pass


class RegistrationNotEligibleError(Exception):
	"""入会資格（pre_member かつ入会費支払済み）を満たさない"""
	pass
