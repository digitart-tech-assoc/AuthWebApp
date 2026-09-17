"use client";

/**
 * DevRoleSwitcher — 開発環境専用のロール切替モーダル
 *
 * 画面右下のフローティングボタンをクリックするとモーダルが開き、
 * ワンクリックで user_memberships + paid_invitations を操作してロールを切り替えられる。
 *
 * NODE_ENV === "development" の場合のみマウントされる（layout.tsx で制御）。
 */

import { useCallback, useEffect, useState } from "react";

/* ─── 型定義 ─── */
type DevState = {
	discord_id: string | null;
	current_role: string;
	is_paid: boolean;
	available_roles: string[];
};

type Preset = {
	label: string;
	emoji: string;
	role: string;
	is_paid: boolean;
	description: string;
};

/* ─── プリセット（指定された7つのペルソナ） ─── */
const PRESETS: Preset[] = [
	{
		label: "admin",
		emoji: "🔴",
		role: "admin",
		is_paid: false,
		description: "管理者権限。全機能・全管理画面にアクセス可能",
	},
	{
		label: "member",
		emoji: "🟢",
		role: "member",
		is_paid: false,
		description: "正会員。通常会員権限・ロール管理等にアクセス可能",
	},
	{
		label: "pre_member",
		emoji: "🟡",
		role: "pre_member",
		is_paid: false,
		description: "Discord参加済み・入会費未払い",
	},
	{
		label: "pre_member+paid",
		emoji: "🟠",
		role: "pre_member",
		is_paid: true,
		description: "Discord参加済み・入会費支払い完了者",
	},
	{
		label: "none",
		emoji: "⚪",
		role: "none",
		is_paid: false,
		description: "新規接触者。メンバーシップなし・未払い",
	},
	{
		label: "obog",
		emoji: "🔵",
		role: "obog",
		is_paid: false,
		description: "卒業生メンバー（OB/OG）",
	},
	{
		label: "sub_user",
		emoji: "🟣",
		role: "sub_user",
		is_paid: false,
		description: "サブユーザー（サブアカウント等）",
	},
];

/* ─── ロール表示色マッピング ─── */
const ROLE_COLORS: Record<string, string> = {
	admin: "#ef4444",
	member: "#22c55e",
	pre_member: "#eab308",
	none: "#a1a1aa",
	obog: "#3b82f6",
	sub_user: "#a855f7",
};

export default function DevRoleSwitcher() {
	const [mounted, setMounted] = useState(false);
	const [isOpen, setIsOpen] = useState(false);
	const [state, setState] = useState<DevState | null>(null);
	const [loading, setLoading] = useState(false);
	const [switching, setSwitching] = useState<string | null>(null);
	const [message, setMessage] = useState<string | null>(null);

	useEffect(() => {
		setMounted(true);
	}, []);

	/* 現在の状態を取得 */
	const fetchState = useCallback(async () => {
		try {
			setLoading(true);
			const res = await fetch("/api/dev/state");
			if (res.ok) {
				const data: DevState = await res.json();
				setState(data);
			}
		} catch (err) {
			console.error("[DevRoleSwitcher] Failed to fetch state:", err);
		} finally {
			setLoading(false);
		}
	}, []);

	/* モーダルを開いたときに状態を取得 */
	useEffect(() => {
		if (isOpen) {
			fetchState();
		}
	}, [isOpen, fetchState]);

	/* ロール切替 */
	const handleSwitch = async (preset: Preset) => {
		const key = `${preset.role}-${preset.is_paid}`;
		setSwitching(key);
		setMessage(null);
		try {
			const res = await fetch("/api/dev/switch-role", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ role: preset.role, is_paid: preset.is_paid }),
			});
			if (res.ok) {
				const data = await res.json();
				setMessage(data.message);
				await fetchState();
				// 1秒後にリロードして反映
				setTimeout(() => {
					window.location.reload();
				}, 800);
			} else {
				const err = await res.json().catch(() => ({ detail: "不明なエラー" }));
				setMessage(`エラー: ${err.detail}`);
			}
		} catch (err) {
			setMessage(`通信エラー: ${err instanceof Error ? err.message : String(err)}`);
		} finally {
			setSwitching(null);
		}
	};

	/* 現在のプリセットと一致するかチェック */
	const isCurrentPreset = (preset: Preset): boolean => {
		if (!state) return false;
		return state.current_role === preset.role && state.is_paid === preset.is_paid;
	};

	const currentColor = state ? (ROLE_COLORS[state.current_role] ?? "#a1a1aa") : "#a1a1aa";

	if (!mounted) return null;

	return (
		<>
			{/* フローティングボタン */}
			<button
				id="dev-role-switcher-trigger"
				onClick={() => setIsOpen(!isOpen)}
				style={{
					position: "fixed",
					bottom: "20px",
					right: "20px",
					zIndex: 99999,
					width: "48px",
					height: "48px",
					borderRadius: "50%",
					border: `3px solid ${currentColor}`,
					background: "rgba(24, 24, 27, 0.9)",
					backdropFilter: "blur(12px)",
					color: "#fff",
					fontSize: "18px",
					cursor: "pointer",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					boxShadow: `0 4px 24px ${currentColor}40, 0 0 0 1px rgba(255,255,255,0.08)`,
					transition: "all 0.2s ease",
				}}
				title="Dev Role Switcher"
			>
				🔑
			</button>

			{/* モーダル */}
			{isOpen && (
				<div
					style={{
						position: "fixed",
						inset: 0,
						zIndex: 99998,
						display: "flex",
						alignItems: "flex-end",
						justifyContent: "flex-end",
						padding: "20px",
					}}
				>
					{/* オーバーレイ */}
					<div
						onClick={() => setIsOpen(false)}
						style={{
							position: "absolute",
							inset: 0,
							background: "rgba(0,0,0,0.3)",
							backdropFilter: "blur(2px)",
						}}
					/>

					{/* モーダル本体 */}
					<div
						id="dev-role-switcher-modal"
						style={{
							position: "relative",
							width: "360px",
							maxHeight: "80vh",
							overflowY: "auto",
							background: "linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
							borderRadius: "16px",
							border: "1px solid rgba(255,255,255,0.1)",
							boxShadow: "0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)",
							padding: "24px",
							fontFamily: "'Inter', -apple-system, sans-serif",
							color: "#e4e4e7",
							marginBottom: "60px",
						}}
					>
						{/* ヘッダー */}
						<div
							style={{
								display: "flex",
								alignItems: "center",
								justifyContent: "space-between",
								marginBottom: "16px",
							}}
						>
							<div>
								<h3
									style={{
										margin: 0,
										fontSize: "16px",
										fontWeight: 700,
										letterSpacing: "-0.02em",
										color: "#fff",
									}}
								>
									🛠️ Dev Role Switcher
								</h3>
								<p
									style={{
										margin: "4px 0 0",
										fontSize: "11px",
										color: "#71717a",
									}}
								>
									開発環境専用 — ロール切替ツール
								</p>
							</div>
							<button
								onClick={() => setIsOpen(false)}
								style={{
									background: "rgba(255,255,255,0.08)",
									border: "none",
									borderRadius: "8px",
									width: "28px",
									height: "28px",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									cursor: "pointer",
									color: "#a1a1aa",
									fontSize: "14px",
								}}
							>
								✕
							</button>
						</div>

						{/* 現在の状態 */}
						{state && (
							<div
								style={{
									background: "rgba(255,255,255,0.05)",
									borderRadius: "10px",
									padding: "12px",
									marginBottom: "16px",
									border: "1px solid rgba(255,255,255,0.06)",
								}}
							>
								<div
									style={{
										display: "flex",
										alignItems: "center",
										gap: "8px",
										fontSize: "12px",
										color: "#a1a1aa",
									}}
								>
									<span>現在のロール:</span>
									<span
										style={{
											display: "inline-flex",
											alignItems: "center",
											gap: "4px",
											padding: "2px 10px",
											borderRadius: "9999px",
											background: `${currentColor}20`,
											color: currentColor,
											fontWeight: 600,
											fontSize: "12px",
											border: `1px solid ${currentColor}40`,
										}}
									>
										<span
											style={{
												width: "6px",
												height: "6px",
												borderRadius: "50%",
												background: currentColor,
											}}
										/>
										{state.current_role}
									</span>
									{state.is_paid && (
										<span
											style={{
												padding: "2px 8px",
												borderRadius: "9999px",
												background: "rgba(234,179,8,0.15)",
												color: "#eab308",
												fontSize: "10px",
												fontWeight: 600,
											}}
										>
											💰 支払済
										</span>
									)}
								</div>
								{state.discord_id && (
									<div
										style={{
											fontSize: "10px",
											color: "#52525b",
											marginTop: "6px",
											fontFamily: "monospace",
										}}
									>
										Discord ID: {state.discord_id}
									</div>
								)}
							</div>
						)}

						{loading && (
							<div
								style={{
									textAlign: "center",
									padding: "20px",
									color: "#71717a",
									fontSize: "13px",
								}}
							>
								読み込み中...
							</div>
						)}

						{/* プリセットボタン */}
						<div
							style={{
								display: "flex",
								flexDirection: "column",
								gap: "6px",
							}}
						>
							{PRESETS.map((preset) => {
								const key = `${preset.role}-${preset.is_paid}`;
								const isCurrent = isCurrentPreset(preset);
								const isLoading = switching === key;
								const color = ROLE_COLORS[preset.role] ?? "#a1a1aa";

								return (
									<button
										key={key}
										id={`dev-switch-${preset.role}${preset.is_paid ? "-paid" : ""}`}
										onClick={() => handleSwitch(preset)}
										disabled={isLoading || isCurrent}
										style={{
											display: "flex",
											alignItems: "center",
											gap: "10px",
											width: "100%",
											padding: "10px 14px",
											borderRadius: "10px",
											border: isCurrent
												? `1.5px solid ${color}`
												: "1px solid rgba(255,255,255,0.06)",
											background: isCurrent
												? `${color}15`
												: "rgba(255,255,255,0.03)",
											color: isCurrent ? color : "#d4d4d8",
											cursor: isCurrent ? "default" : "pointer",
											opacity: isLoading ? 0.6 : 1,
											transition: "all 0.15s ease",
											textAlign: "left",
											fontFamily: "inherit",
											fontSize: "13px",
										}}
										onMouseEnter={(e) => {
											if (!isCurrent) {
												(e.currentTarget as HTMLButtonElement).style.background =
													"rgba(255,255,255,0.07)";
											}
										}}
										onMouseLeave={(e) => {
											if (!isCurrent) {
												(e.currentTarget as HTMLButtonElement).style.background =
													"rgba(255,255,255,0.03)";
											}
										}}
									>
										<span style={{ fontSize: "16px", flexShrink: 0 }}>
											{preset.emoji}
										</span>
										<div style={{ flex: 1, minWidth: 0 }}>
											<div
												style={{
													fontWeight: 600,
													fontSize: "13px",
													lineHeight: "1.3",
												}}
											>
												{preset.label}
												{isCurrent && (
													<span
														style={{
															marginLeft: "6px",
															fontSize: "10px",
															fontWeight: 400,
															opacity: 0.7,
														}}
													>
														✓ 現在
													</span>
												)}
											</div>
											<div
												style={{
													fontSize: "10px",
													color: "#71717a",
													lineHeight: "1.4",
													marginTop: "1px",
												}}
											>
												{preset.description}
											</div>
										</div>
										{isLoading && (
											<span
												style={{
													fontSize: "12px",
													animation: "spin 1s linear infinite",
												}}
											>
												⏳
											</span>
										)}
									</button>
								);
							})}
						</div>

						{/* メッセージ */}
						{message && (
							<div
								style={{
									marginTop: "12px",
									padding: "10px 12px",
									borderRadius: "8px",
									background: message.startsWith("エラー") || message.startsWith("通信エラー")
										? "rgba(239,68,68,0.1)"
										: "rgba(34,197,94,0.1)",
									border: `1px solid ${
										message.startsWith("エラー") || message.startsWith("通信エラー")
											? "rgba(239,68,68,0.2)"
											: "rgba(34,197,94,0.2)"
									}`,
									color: message.startsWith("エラー") || message.startsWith("通信エラー")
										? "#fca5a5"
										: "#86efac",
									fontSize: "12px",
									lineHeight: "1.4",
								}}
							>
								{message}
							</div>
						)}

						{/* フッター */}
						<div
							style={{
								marginTop: "16px",
								paddingTop: "12px",
								borderTop: "1px solid rgba(255,255,255,0.06)",
								fontSize: "10px",
								color: "#3f3f46",
								textAlign: "center",
							}}
						>
							このツールは開発環境でのみ表示されます
						</div>
					</div>
				</div>
			)}
		</>
	);
}
