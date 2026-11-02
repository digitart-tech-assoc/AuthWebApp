/**
 * 内部サービス間通信用シークレット（SHARED_SECRET）の検証。
 * Backend・Discord Bot と同じ規則（#80）: 本番では未設定または16文字未満なら起動しない。
 * メッセージには秘密情報を含めないため、値や長さは出さない。
 */

const MIN_SHARED_SECRET_LENGTH = 16;

function isProduction(): boolean {
	return process.env.NODE_ENV === "production";
}

function weakSecretReason(secret: string): string | null {
	if (!secret) {
		return "SHARED_SECRET is not set";
	}
	if (secret.length < MIN_SHARED_SECRET_LENGTH) {
		return `SHARED_SECRET must be at least ${MIN_SHARED_SECRET_LENGTH} characters`;
	}
	return null;
}

/** サーバー起動時に呼ぶ。本番で SHARED_SECRET が弱い場合は例外を投げ、それ以外では警告する。 */
export function validateSharedSecret(): void {
	const reason = weakSecretReason(process.env.SHARED_SECRET ?? "");
	if (!reason) {
		return;
	}
	if (isProduction()) {
		throw new Error(reason);
	}
	console.warn(`${reason} (allowed only outside production)`);
}

/** 使用可能な SHARED_SECRET を返す。未設定、または本番で弱い値の場合は null。 */
export function getSharedSecret(): string | null {
	const secret = process.env.SHARED_SECRET ?? "";
	if (!secret || (isProduction() && weakSecretReason(secret))) {
		return null;
	}
	return secret;
}
