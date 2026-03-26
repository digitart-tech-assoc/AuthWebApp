import Link from "next/link";
import styles from "../../join/join.module.css";

export default function JoinFormSelectPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>入会フォーム</h1>
        <p className={styles.lead}>該当する区分を選択してください。選択後、それぞれの入力フォームへ遷移します。</p>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <h2 className={styles.cardTitle}>青山学院大学の学生</h2>
          <p className={styles.cardText}>在学生向けの入会フォームです。学部・学科・学年の入力欄があります。</p>
          <Link className={styles.primary} href="/join/form/aoyama-student">
            このフォームへ進む
          </Link>
        </article>

        <article className={styles.card}>
          <h2 className={styles.cardTitle}>青山学院大学入学見込みの方</h2>
          <p className={styles.cardText}>入学予定者向けのフォームです。入学予定年度などを入力します。</p>
          <Link className={styles.primary} href="/join/form/prospective-student">
            このフォームへ進む
          </Link>
        </article>

        <article className={styles.card}>
          <h2 className={styles.cardTitle}>その他</h2>
          <p className={styles.cardText}>上記に当てはまらない方向けのフォームです。自由記述で補足可能です。</p>
          <Link className={styles.primary} href="/join/form/other">
            このフォームへ進む
          </Link>
        </article>
      </section>
    </main>
  );
}
