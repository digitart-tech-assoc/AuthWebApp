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
		<main style={{ padding: 24 }}>
			<h1>Sign in</h1>
			{errorMessage && (
				<p style={{ color: "#b91c1c", marginBottom: 12 }}>
					{errorMessage}
				</p>
			)}
			<p style={{ marginBottom: 12 }}>Discord アカウントでログインしてください。</p>
			<a
				href={`/auth/login/discord?callbackUrl=${encodeURIComponent(callbackUrl)}`}
				style={{
					display: "inline-block",
					padding: "10px 20px",
					background: "#5865F2",
					color: "#fff",
					borderRadius: 6,
					textDecoration: "none",
					fontWeight: 600,
				}}
			>
				Discord でログイン
			</a>
		</main>
	);
}