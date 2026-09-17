"use client";

/**
 * DevRoleSwitcher — 開発環境専用のロール切替モーダル
 *
 * 画面右下のフローティングボタンをクリックするとモーダルが開き、
 * 7つの権限（admin / member / pre_member / pre_member+paid / none / obog / sub_user）
 * をワンクリックで切り替えることができる。
 *
 * 既存のWebページに合わせた、白基調でシンプルなデザイン。
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

/* ─── プリセット ─── */
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

/* ─── ロール表示色マッピング（白背景用） ─── */
const ROLE_COLORS: Record<string, string> = {
	admin: "#dc2626",
	member: "#16a34a",
	pre_member: "#d97706",
	none: "#64748b",
	obog: "#2563eb",
	sub_user: "#7c3aed",
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
				// 反映のためリロード
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

	const currentColor = state ? (ROLE_COLORS[state.current_role] ?? "#64748b") : "#64748b";

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
				onMouseEnter={(e) => {
					e.currentTarget.style.transform = "scale(1.06)";
					e.currentTarget.style.borderColor = "rgba(49, 49, 56, 0.9)";
				}}
				onMouseLeave={(e) => {
					e.currentTarget.style.transform = "scale(1)";
					e.currentTarget.style.borderColor = "rgba(24, 24, 27, 0.9)";
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
							background: "rgba(0, 0, 0, 0.3)",
							backdropFilter: "blur(3px)",
						}}
					/>

					{/* モーダル本体（白基調・シンプル） */}
					<div
						id="dev-role-switcher-modal"
						style={{
							position: "relative",
							width: "360px",
							maxHeight: "82vh",
							overflowY: "auto",
							background: "#ffffff",
							borderRadius: "12px",
							border: "1px solid #e2e8f0",
							boxShadow: "0 20px 40px -8px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.06)",
							padding: "20px",
							fontFamily: "inherit",
							color: "#0f172a",
							marginBottom: "55px",
						}}
					>
						{/* ヘッダー */}
						<div
							style={{
								display: "flex",
								alignItems: "flex-start",
								justifyContent: "space-between",
								paddingBottom: "12px",
								marginBottom: "14px",
								borderBottom: "1px solid #f1f5f9",
							}}
						>
							<div>
								<h3
									style={{
										margin: 0,
										fontSize: "15px",
										fontWeight: 700,
										letterSpacing: "-0.01em",
										color: "#0f172a",
									}}
								>
									🛠️ Dev Role Switcher
								</h3>
								<p
									style={{
										margin: "2px 0 0",
										fontSize: "11px",
										color: "#64748b",
									}}
								>
									開発環境専用 — 権限切替
								</p>
							</div>
							<button
								onClick={() => setIsOpen(false)}
								style={{
									background: "#f8fafc",
									border: "1px solid #e2e8f0",
									borderRadius: "6px",
									width: "26px",
									height: "26px",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									cursor: "pointer",
									color: "#64748b",
									fontSize: "13px",
									transition: "all 0.15s ease",
								}}
								onMouseEnter={(e) => {
									e.currentTarget.style.background = "#f1f5f9";
									e.currentTarget.style.color = "#0f172a";
								}}
								onMouseLeave={(e) => {
									e.currentTarget.style.background = "#f8fafc";
									e.currentTarget.style.color = "#64748b";
								}}
							>
								✕
							</button>
						</div>

						{/* 現在の状態 */}
						{state && (
							<div
								style={{
									background: "#f8fafc",
									borderRadius: "8px",
									padding: "10px 12px",
									marginBottom: "14px",
									border: "1px solid #e2e8f0",
								}}
							>
								<div
									style={{
										display: "flex",
										alignItems: "center",
										gap: "8px",
										fontSize: "12px",
										color: "#475569",
									}}
								>
									<span style={{ fontSize: "12px" }}>現在のロール:</span>
									<span
										style={{
											display: "inline-flex",
											alignItems: "center",
											gap: "5px",
											padding: "2px 8px",
											borderRadius: "9999px",
											background: `${currentColor}12`,
											color: currentColor,
											fontWeight: 600,
											fontSize: "12px",
											border: `1px solid ${currentColor}30`,
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
												padding: "2px 7px",
												borderRadius: "9999px",
												background: "#fef3c7",
												border: "1px solid #fde68a",
												color: "#b45309",
												fontSize: "11px",
												fontWeight: 600,
											}}
										>
											💰 支払済
										</span>
									)}
								</div>
								{state.discord_id ? (
									<div
										style={{
											fontSize: "11px",
											color: "#94a3b8",
											marginTop: "5px",
											fontFamily: "monospace",
										}}
									>
										Discord ID: {state.discord_id}
									</div>
								) : (
									<div
										style={{
											fontSize: "11px",
											color: "#d97706",
											marginTop: "5px",
										}}
									>
										⚠️ 未ログイン（ロール切替にはDiscordログインが必要です）
									</div>
								)}
							</div>
						)}

						{loading && !state && (
							<div
								style={{
									textAlign: "center",
									padding: "18px",
									color: "#64748b",
									fontSize: "13px",
								}}
							>
								読み込み中...
							</div>
						)}

						{/* プリセット一覧 */}
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
								const color = ROLE_COLORS[preset.role] ?? "#64748b";

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
											padding: "9px 12px",
											borderRadius: "8px",
											border: isCurrent
												? `1.5px solid ${color}`
												: "1px solid #e2e8f0",
											background: isCurrent
												? `${color}0c`
												: "#ffffff",
											color: "#0f172a",
											cursor: isCurrent ? "default" : "pointer",
											opacity: isLoading ? 0.6 : 1,
											transition: "all 0.15s ease",
											textAlign: "left",
											fontFamily: "inherit",
										}}
										onMouseEnter={(e) => {
											if (!isCurrent) {
												e.currentTarget.style.background = "#f8fafc";
												e.currentTarget.style.borderColor = "#cbd5e1";
											}
										}}
										onMouseLeave={(e) => {
											if (!isCurrent) {
												e.currentTarget.style.background = "#ffffff";
												e.currentTarget.style.borderColor = "#e2e8f0";
											}
										}}
									>
										<span style={{ fontSize: "15px", flexShrink: 0 }}>
											{preset.emoji}
										</span>
										<div style={{ flex: 1, minWidth: 0 }}>
											<div
												style={{
													fontWeight: 600,
													fontSize: "13px",
													lineHeight: "1.3",
													display: "flex",
													alignItems: "center",
													gap: "6px",
												}}
											>
												<span style={{ color: isCurrent ? color : "#0f172a" }}>
													{preset.label}
												</span>
												{isCurrent && (
													<span
														style={{
															fontSize: "11px",
															fontWeight: 600,
															color: color,
														}}
													>
														✓ 現在
													</span>
												)}
											</div>
											<div
												style={{
													fontSize: "11px",
													color: "#64748b",
													lineHeight: "1.3",
													marginTop: "2px",
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

						{/* 通知メッセージ */}
						{message && (
							<div
								style={{
									marginTop: "12px",
									padding: "9px 12px",
									borderRadius: "8px",
									background: message.startsWith("エラー") || message.startsWith("通信エラー")
										? "#fef2f2"
										: "#f0fdf4",
									border: `1px solid ${
										message.startsWith("エラー") || message.startsWith("通信エラー")
											? "#fecaca"
											: "#bbf7d0"
									}`,
									color: message.startsWith("エラー") || message.startsWith("通信エラー")
										? "#991b1b"
										: "#166534",
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
								marginTop: "14px",
								paddingTop: "10px",
								borderTop: "1px solid #f1f5f9",
								fontSize: "11px",
								color: "#94a3b8",
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
