import Link from "next/link";
import styles from "./join.module.css";

export default function JoinGuidePage() {
	return (
		<main className={styles.page}>
			<section className={styles.hero}>
				<h1 className={styles.title}>入会・案内ページ</h1>
				<p className={styles.lead}>
					サインイン後の判定結果に応じて、この導線から必要なページへ遷移します。
				</p>
				<p className={styles.notice}>
					member / obog 権限保持者は roles へ、入会予定者は入会フォームへ、
					対象外は非会員メッセージへ遷移する想定です。
				</p>
			</section>

			<section className={styles.grid}>
				<article className={styles.card}>
					<h2 className={styles.cardTitle}>入会フォーム</h2>
					<p className={styles.cardText}>
						在学生・入学見込み・その他の3区分からフォームを選択します。
					</p>
					<Link className={styles.primary} href="/join/form">
						入会フォームへ
					</Link>
				</article>

				<article className={styles.card}>
					<h2 className={styles.cardTitle}>非会員向けメッセージ</h2>
					<p className={styles.cardText}>
						対象外ユーザー向けの案内文と、入会・お問い合わせへのリンクを表示します。
					</p>
					<Link className={styles.secondary} href="/non-member">
						メッセージを確認
					</Link>
				</article>

				<article className={styles.card}>
					<h2 className={styles.cardTitle}>お問い合わせ</h2>
					<p className={styles.cardText}>
						連絡先・氏名・所属・件名・本文を入力する問い合わせフォームです。
					</p>
					<Link className={styles.secondary} href="/contact">
						お問い合わせへ
					</Link>
				</article>
			</section>
		</main>
	);
}
