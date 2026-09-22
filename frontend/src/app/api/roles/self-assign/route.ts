import { NextResponse } from "next/server";

export async function POST() {
	return NextResponse.json(
		{
			ok: false,
			detail: "This endpoint has been deprecated and removed. Please use /api/roles/self-batch instead.",
		},
		{ status: 410 }
	);
}
