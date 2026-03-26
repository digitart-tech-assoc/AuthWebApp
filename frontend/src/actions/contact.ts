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
	const res = await fetchBackend("/api/v1/contact/submit", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(payload),
	});

	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error((errorData as { detail?: string }).detail || "お問い合わせの送信に失敗しました");
	}

	const data = (await res.json()) as ContactResponse;
	return data;
}
