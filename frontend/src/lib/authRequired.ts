/**
 * AUTH_REQUIRED（認証強制フラグ）の判定。
 * AUTH_REQUIRED=false では未ログインのリクエストを SHARED_SECRET（admin 相当）でバックエンドへ送るため、
 * 本番では認められない。起動時に止め、万一起動しても常に認証必須として扱う（#80）。
 */

function isProduction(): boolean {
	return process.env.NODE_ENV === "production";
}

/** 認証を必須とするか。本番では AUTH_REQUIRED の値にかかわらず true。 */
export function isAuthRequired(): boolean {
	return isProduction() || process.env.AUTH_REQUIRED !== "false";
}

/** サーバー起動時に呼ぶ。本番で AUTH_REQUIRED=false の場合は例外を投げる。 */
export function validateAuthRequired(): void {
	if (isProduction() && process.env.AUTH_REQUIRED === "false") {
		throw new Error("AUTH_REQUIRED=false is not allowed in production");
	}
}
