class OTPTooManyAttemptsError(ValueError):
	pass


class RegistrationNotEligibleError(Exception):
	"""入会資格（pre_member かつ入会費支払済み）を満たさない"""
	pass
