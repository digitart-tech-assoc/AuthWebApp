// 役割: お問い合わせ送信
"use server";

import { type ActionResult, messageForStatus } from "@/lib/errorMessages";
import { fetchBackend } from "@/lib/backendFetch";
import { getForwardedForHeader } from "@/lib/forwardedHeaders";

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

const CONTACT_ERROR_MESSAGES = {
	422: "入力内容を確認してください。",
	429: "送信回数の上限に達しました。しばらく時間をおいてから再度お試しください。",
	default: "お問い合わせの送信に失敗しました。時間をおいて再度お試しください。",
};

export async function submitContact(payload: ContactPayload): Promise<ActionResult<ContactResponse>> {
	// Backend のエラー文言は返さず、固定文言を返す（詳細は Backend のログで確認する）
	try {
		const res = await fetchBackend("/api/v1/contact/submit", {
			method: "POST",
			headers: {
				...(await getForwardedForHeader()),
				"Content-Type": "application/json",
			},
			body: JSON.stringify(payload),
		});

		if (!res.ok) {
			return { ok: false, error: messageForStatus(res.status, CONTACT_ERROR_MESSAGES) };
		}

		return { ok: true, data: (await res.json()) as ContactResponse };
	} catch {
		return { ok: false, error: CONTACT_ERROR_MESSAGES.default };
	}
}
