type LoginPageProps = {
	searchParams?:
		| {
			callbackUrl?: string;
		  }
		| Promise<{
				callbackUrl?: string;
		  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
	const params = await Promise.resolve(searchParams);
	const callbackUrl = params?.callbackUrl || "/roles";

	return (
		<main style={{ padding: 24 }}>
			<h1>Sign in</h1>
			<p style={{ marginBottom: 12 }}>Keycloak でログインしてください。</p>
			<form method="POST" action="/api/login/keycloak">
				<input type="hidden" name="callbackUrl" value={callbackUrl} />
				<button type="submit">Sign in with Keycloak</button>
			</form>
		</main>
	);
}