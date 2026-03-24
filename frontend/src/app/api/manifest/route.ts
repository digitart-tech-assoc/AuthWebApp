import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function PUT(request: Request) {
	try {
		const payload = await request.json();
		const res = await fetch(`${BACKEND_URL}/api/v1/manifest`, {
			method: "PUT",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
			cache: "no-store",
		});
		const body = await res.json();
		return NextResponse.json(body, { status: res.status });
	} catch {
		return NextResponse.json({ ok: false, detail: "manifest proxy failed" }, { status: 502 });
	}
}
