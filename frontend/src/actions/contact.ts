// 役割: お問い合わせ送信
"use server";

import { fetchBackend } from "@/lib/backendFetch";

export interface ContactPayload {
	email: string;
	name: string;
	subject?: string | null;
	affiliation?: string | null;
	message?: string | null;
}

export interface ContactResponse {
	status: string;
	message: string;
	message_id?: string;
}

export async function submitContact(payload: ContactPayload): Promise<ContactResponse> {
	console.log("[Contact] Submitting contact form:", JSON.stringify(payload, null, 2));
	
	try {
		const url = "/api/v1/contact/submit";
		console.log("[Contact] Fetching from:", url);
		
		const res = await fetchBackend(url, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(payload),
		});

		console.log("[Contact] Response status:", res.status);
		console.log("[Contact] Response headers:", Object.fromEntries(res.headers));

		if (!res.ok) {
			const errorData = await res.json().catch(() => ({}));
			const errorMsg = (errorData as { detail?: string }).detail || `HTTP ${res.status}: ${res.statusText}`;
			console.error("[Contact] API error:", errorMsg);
			throw new Error(errorMsg);
		}

		const data = (await res.json()) as ContactResponse;
		console.log("[Contact] Success response:", data);
		return data;
	} catch (error) {
		const errorMsg = error instanceof Error ? error.message : String(error);
		console.error("[Contact] Submission failed:", errorMsg);
		throw error;
	}
}
