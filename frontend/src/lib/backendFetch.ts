// This module must be usable from both Client and Server components.
// Do not import `server-only` here so it can be bundled for the browser.
const PRIMARY_BACKEND_URL = ((): string => {
	if (typeof window === "undefined") {
		// Server runtime: use BACKEND_URL if set
		return process.env.BACKEND_URL ?? "http://localhost:8000";
	}
	// Client/runtime: use NEXT_PUBLIC_BACKEND_URL which is exposed to the browser
	// fallback to same-origin backend assumption
	return (process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000").trim();
})();

const FALLBACK_BACKEND_URL = ((): string => {
	if (typeof window === "undefined") {
		return process.env.BACKEND_FALLBACK_URL ?? "http://localhost:8000";
	}
	return (process.env.NEXT_PUBLIC_BACKEND_FALLBACK_URL ?? "http://localhost:8000").trim();
})();

function buildBackendCandidates(): string[] {
	const candidates = [PRIMARY_BACKEND_URL, FALLBACK_BACKEND_URL]
		.map((value) => value.trim())
		.filter((value) => value.length > 0);
	return [...new Set(candidates)];
}

function isRetryableNetworkError(error: unknown): boolean {
	if (!(error instanceof Error)) {
		return false;
	}
	const text = `${error.name} ${error.message}`;
	return text.includes("ENOTFOUND") || text.includes("ECONNREFUSED") || text.includes("fetch failed");
}

export async function fetchBackend(path: string, init?: RequestInit): Promise<Response> {
	const errors: string[] = [];

	for (const baseUrl of buildBackendCandidates()) {
		const normalizedPath = path.startsWith("/") ? path : `/${path}`;
		const url = `${baseUrl}${normalizedPath}`;
		try {
			return await fetch(url, init);
		} catch (error) {
			errors.push(`${url}: ${error instanceof Error ? error.message : String(error)}`);
			if (!isRetryableNetworkError(error)) {
				throw error;
			}
		}
	}

	throw new Error(`backend unreachable: ${errors.join(" | ")}`);
}