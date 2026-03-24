import "server-only";

const PRIMARY_BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const FALLBACK_BACKEND_URL = process.env.BACKEND_FALLBACK_URL ?? "http://localhost:8000";

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