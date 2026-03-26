import Link from "next/link";
import styles from "../join/join.module.css";

export default function NonMemberPage() {
  return (
    <main className={styles.page}>
      <section className={`${styles.hero} ${styles.heroNonMember}`}>
        <div className={styles.heroContent}>
          <div>
            <h1 className={styles.title}>Digitart テクノロジー愛好会へようこそ</h1>
            <p className={styles.kicker}>青山学院大学の学生による、学びと交流のコミュニティ</p>
            <p className={styles.lead}>テクノロジーに興味がある学生が集い、ワークショップやハッカソン、勉強会を開催しています。興味のある方は仮入会から参加してください。</p>

            <div className={styles.actions} style={{ marginTop: 20 }}>
              <Link className={styles.primary} href="/join/form">
                入会フォームへ
              </Link>
              <Link className={styles.secondary} href="/contact">
                お問い合わせ
              </Link>
            </div>
          </div>

          <div className={styles.heroCard} aria-hidden>
            <div className={styles.badge}>メンバー特典</div>
            <h3 className={styles.cardTitle}>イベント参加・Discord招待</h3>
            <p className={styles.cardText}>入会後、コミュニティ限定イベントや資料、Discordでの交流に参加できます。</p>
            <div style={{ marginTop: 12 }}>
              <Link className={styles.secondary} href="/join/form">今すぐ仮入会</Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
