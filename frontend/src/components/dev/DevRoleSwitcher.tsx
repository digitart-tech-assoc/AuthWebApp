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
import styles from "./DevRoleSwitcher.module.css";

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
				className={styles.trigger}
				style={{
					border: `3px solid ${currentColor}`,
					boxShadow: `0 4px 24px ${currentColor}40, 0 0 0 1px rgba(255,255,255,0.08)`,
				}}
				title="Dev Role Switcher"
			>
				🔑
			</button>

			{/* モーダル */}
			{isOpen && (
				<div className={styles.overlayWrapper}>
					{/* オーバーレイ */}
					<div className={styles.overlay} onClick={() => setIsOpen(false)} />

					{/* モーダル本体（白基調・シンプル） */}
					<div id="dev-role-switcher-modal" className={styles.modal}>
						{/* ヘッダー */}
						<div className={styles.header}>
							<div>
								<h3 className={styles.headerTitle}>🛠️ Dev Role Switcher</h3>
								<p className={styles.headerSubtitle}>開発環境専用 — 権限切替</p>
							</div>
							<button onClick={() => setIsOpen(false)} className={styles.closeButton}>
								✕
							</button>
						</div>

						{/* 現在の状態 */}
						{state && (
							<div className={styles.stateBox}>
								<div className={styles.stateRow}>
									<span className={styles.stateLabel}>現在のロール:</span>
									<span
										className={styles.roleBadge}
										style={{
											background: `${currentColor}12`,
											color: currentColor,
											border: `1px solid ${currentColor}30`,
										}}
									>
										<span className={styles.roleBadgeDot} style={{ background: currentColor }} />
										{state.current_role}
									</span>
									{state.is_paid && <span className={styles.paidBadge}>💰 支払済</span>}
								</div>
								{state.discord_id ? (
									<div className={styles.discordId}>Discord ID: {state.discord_id}</div>
								) : (
									<div className={styles.notLoggedIn}>
										⚠️ 未ログイン（ロール切替にはDiscordログインが必要です）
									</div>
								)}
							</div>
						)}

						{loading && !state && (
							<div className={styles.loadingBox}>読み込み中...</div>
						)}

						{/* プリセット一覧 */}
						<div className={styles.presetList}>
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
										className={styles.presetButton}
										style={{
											border: isCurrent ? `1.5px solid ${color}` : "1px solid #e2e8f0",
											background: isCurrent ? `${color}0c` : "#ffffff",
											color: "#0f172a",
											cursor: isCurrent ? "default" : "pointer",
											opacity: isLoading ? 0.6 : 1,
										}}
									>
										<span className={styles.presetEmoji}>{preset.emoji}</span>
										<div className={styles.presetContent}>
											<div className={styles.presetLabelRow}>
												<span style={{ color: isCurrent ? color : "#0f172a" }}>
													{preset.label}
												</span>
												{isCurrent && (
													<span className={styles.currentBadge} style={{ color }}>
														✓ 現在
													</span>
												)}
											</div>
											<div className={styles.presetDescription}>{preset.description}</div>
										</div>
										{isLoading && <span style={{ fontSize: "12px" }}>⏳</span>}
									</button>
								);
							})}
						</div>

						{/* 通知メッセージ */}
						{message && (
							<div
								className={`${styles.messageBox} ${
									message.startsWith("エラー") || message.startsWith("通信エラー")
										? styles.messageError
										: styles.messageSuccess
								}`}
							>
								{message}
							</div>
						)}

						{/* フッター */}
						<div className={styles.footer}>
							このツールは開発環境でのみ表示されます
						</div>
					</div>
				</div>
			)}
		</>
	);
}
