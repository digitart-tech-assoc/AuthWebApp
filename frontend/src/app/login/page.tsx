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
		<main className="mx-auto w-full max-w-5xl px-4 py-8 sm:py-12">
			<h1 className="mb-4 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Sign in</h1>
			{errorMessage && (
				<div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
					{errorMessage}
				</div>
			)}
			<p className="mb-6 text-sm text-slate-600">Discord アカウントでログインしてください。</p>
			<a
				href={`/auth/login/discord?callbackUrl=${encodeURIComponent(callbackUrl)}`}
				className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-[#5865F2] px-5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#4752C4] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5865F2] focus-visible:ring-offset-2 no-underline"
			>
				Discord でログイン
			</a>
		</main>
	);
}