import Link from "next/link";
import styles from "../join.module.css";

export default function JoinFormSelectionPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>入会フォーム（仮入会）</h1>
        <p className={styles.lead}>在学生・入学見込み・その他の3区分から該当するフォームを選択してください。</p>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <h2 className={styles.cardTitle}>在学生（青山学院大学）</h2>
          <p className={styles.cardText}>学生番号から学内メールを自動補完します。</p>
          <Link className={styles.primary} href="/join/form/aoyama-student">フォームへ</Link>
        </article>

        <article className={styles.card}>
          <h2 className={styles.cardTitle}>入学見込み</h2>
          <p className={styles.cardText}>入学予定年度とメールで仮入会の認証を行います。</p>
          <Link className={styles.primary} href="/join/form/prospective-student">フォームへ</Link>
        </article>

        <article className={styles.card}>
          <h2 className={styles.cardTitle}>その他</h2>
          <p className={styles.cardText}>青山学院大学以外の方へは案内を表示します。</p>
          <Link className={styles.secondary} href="/join/form/other">案内を見る</Link>
        </article>
      </section>
    </main>
  );
}

