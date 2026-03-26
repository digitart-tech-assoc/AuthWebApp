// 役割: 非会員ユーザー向けメッセージ・誘導ページ

import { auth } from "@/auth";
import { redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const SHARED_SECRET = process.env.SHARED_SECRET ?? "dev-secret";

async function resolveRoleFromBackend(
	accessToken: string | undefined,
	sub: string | undefined,
	fallbackRole: string,
): Promise<string> {
	if (accessToken) {
		try {
			const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
				headers: { Authorization: `Bearer ${accessToken}` },
				cache: "no-store",
			});
			if (res.ok) {
				const data = (await res.json()) as { app_role?: string };
				return data.app_role ?? fallbackRole;
			}
		} catch {
			// フォールバックへ
		}
	}

	try {
		if (!sub) {
			return fallbackRole;
		}
		const url = `${BACKEND_URL}/api/v1/auth/role-by-sub?sub=${encodeURIComponent(sub)}`;
		const res = await fetch(url, {
			headers: { Authorization: `Bearer ${SHARED_SECRET}` },
			cache: "no-store",
		});
		if (!res.ok) {
			return fallbackRole;
		}
		const data = (await res.json()) as { app_role?: string };
		return data.app_role ?? fallbackRole;
	} catch {
		return fallbackRole;
	}
}

export default async function JoinPage() {
	const session = await auth();
	const sessionData = session as typeof session & {
		accessToken?: string;
		user?: { role?: string; discordId?: string | null; name?: string | null; sub?: string };
	};
	const fallbackRole = sessionData?.user?.role ?? "none";
	const role = await resolveRoleFromBackend(sessionData?.accessToken, sessionData?.user?.sub, fallbackRole);

	// 既に会員の場合はリダイレクト
	if (role && ["member", "admin", "obog"].includes(role)) {
		redirect("/roles");
	}

	const isPaid = false; // TODO: バックエンドで確認（将来実装）

	return (
		<main
			style={{
				maxWidth: 640,
				margin: "60px auto",
				padding: "0 24px",
				fontFamily: "sans-serif",
				lineHeight: 1.8,
			}}
		>
			<h1 style={{ fontSize: 24, marginBottom: 16 }}>
				digitart テクノロジー愛好会へようこそ
			</h1>

			<p style={{ color: "#555", marginBottom: 24 }}>
				このページはDigitartテクノロジー愛好会のメンバー専用ページです。
				現在、あなたのアカウントはメンバー登録されていません。
			</p>

			{isPaid ? (
				<section
					style={{
						background: "#f0fdf4",
						border: "1px solid #86efac",
						borderRadius: 8,
						padding: 20,
						marginBottom: 24,
					}}
				>
					<h2 style={{ fontSize: 18, marginBottom: 8, color: "#166534" }}>
						入会費のお支払いを確認しました
					</h2>
					<p style={{ color: "#166534" }}>
						以下のフォームから情報を入力して会員登録を完了してください。
					</p>
					<a
						href="/join/form"
						style={{
							display: "inline-block",
							marginTop: 12,
							padding: "10px 24px",
							background: "#16a34a",
							color: "white",
							borderRadius: 6,
							textDecoration: "none",
							fontWeight: "bold",
						}}
					>
						入会フォームへ →
					</a>
				</section>
			) : (
				<section
					style={{
						background: "#fafafa",
						border: "1px solid #e5e7eb",
						borderRadius: 8,
						padding: 20,
						marginBottom: 24,
					}}
				>
					<p style={{ marginBottom: 12 }}>
						thanks for visiting digitartテクノロジー愛好会!!
					</p>
					<p style={{ marginBottom: 12 }}>
						digitartテクノロジー愛好会は青山学院大学の学生団体です。テクノロジーに興味がある青山学院大学の学生であれば誰でも入会の手続きができます。
					</p>
					<p style={{ marginBottom: 20 }}>
						入会を希望する方は、こちら（
						<a href="/join/form" style={{ color: "#2563eb" }}>
							入会フォーム
						</a>
						）から仮会員として参加してください。
						当会の活動内容はホームページに記載しております。
						その他、お問い合わせのある方はフォームよりご質問ください。
					</p>

					<div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
						<a
							href="/join/form"
							style={{
								padding: "10px 20px",
								background: "#2563eb",
								color: "white",
								borderRadius: 6,
								textDecoration: "none",
								fontWeight: "bold",
							}}
						>
							入会フォーム
						</a>
						<a
							href="/contact"
							style={{
								padding: "10px 20px",
								background: "#6b7280",
								color: "white",
								borderRadius: 6,
								textDecoration: "none",
								fontWeight: "bold",
							}}
						>
							お問い合わせフォーム
						</a>
					</div>
				</section>
			)}

			<p style={{ fontSize: 13, color: "#9ca3af" }}>
				Discordアカウント: {sessionData?.user?.discordId ?? (sessionData?.user?.name ?? "不明")}
			</p>
		</main>
	);
}
