type LoginPageProps = {
	searchParams?:
		| { callbackUrl?: string; error?: string }
		| Promise<{ callbackUrl?: string; error?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
	const params = await Promise.resolve(searchParams);
	const callbackUrl = params?.callbackUrl ?? "/roles";
	const error = params?.error;
	const errorMessage =
		error === "auth_callback_error"
			? "認証に失敗しました。もう一度お試しください。"
			: error === "discord_email_required"
				? "Discord アカウントにメールアドレスが登録されていないため、ログインできません。Discord 側でメールアドレスを登録してから再度お試しください。"
				: error
					? "エラーが発生しました。"
					: null;

	return (
		<main className="p-6">
			<h1>Sign in</h1>
			{errorMessage && (
				<p className="text-[#b91c1c] mb-3">
					{errorMessage}
				</p>
			)}
			<p className="mb-3">Discord アカウントでログインしてください。</p>
			<a
				href={`/auth/login/discord?callbackUrl=${encodeURIComponent(callbackUrl)}`}
				className="inline-block px-5 py-2.5 bg-[#5865F2] hover:bg-[#4752C4] text-white rounded-[6px] no-underline font-semibold transition-colors"
			>
				Discord でログイン
			</a>
		</main>
	);
}