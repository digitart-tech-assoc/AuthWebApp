/** Next.js サーバーの起動時に 1 回呼ばれる。 */
export async function register() {
	// Edge ランタイム（middleware）でも呼ばれるため、Node.js の API を使う処理は Node.js サーバーでのみ読み込む
	if (process.env.NEXT_RUNTIME === "nodejs") {
		const { validateOnStartup } = await import("./instrumentation-node");
		validateOnStartup();
	}
}
