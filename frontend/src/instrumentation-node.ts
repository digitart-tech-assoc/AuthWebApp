import { validateSharedSecret } from "@/lib/sharedSecret";

/**
 * Node.js サーバーの起動時の検証。
 * register() で例外を投げてもプロセスは終了せず全リクエストが 500 になるだけのため、
 * 本番で設定が不正な場合は明示的に終了して起動を止める（#80）。
 */
export function validateOnStartup(): void {
	try {
		validateSharedSecret();
	} catch (error) {
		// validateSharedSecret のメッセージには秘密情報を含めていない
		console.error(`${error instanceof Error ? error.message : "Invalid configuration"}. Exiting.`);
		process.exit(1);
	}
}
