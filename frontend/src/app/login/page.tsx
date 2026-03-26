type LoginPageProps = {
	searchParams?:
		| { callbackUrl?: string; error?: string }
		| Promise<{ callbackUrl?: string; error?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
	const params = await Promise.resolve(searchParams);
	const callbackUrl = params?.callbackUrl ?? "/roles";
	const error = params?.error;

	return (
		<main style={{ padding: 24 }}>
			<h1>Sign in</h1>
			{error && (
				<p style={{ color: "#b91c1c", marginBottom: 12 }}>
					{error === "auth_callback_error"
						? "認証に失敗しました。もう一度お試しください。"
						: "エラーが発生しました。"}
				</p>
			)}
			<p style={{ marginBottom: 12 }}>Discord アカウントでログインしてください。</p>
			<a
				href={`/api/login/discord?callbackUrl=${encodeURIComponent(callbackUrl)}`}
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