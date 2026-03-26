import Link from "next/link";
import styles from "../../../join/join.module.css";

export default function OtherApplicantFormPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>その他</h1>
      </section>

      <section className={styles.card}>
        <p className={styles.cardText}>
          digitartテクノロジー愛好会に興味を持ってくださりありがとうございます。
          当団体は青山学院大学の学生のみ入会できます。質問等ございましたら
          <Link href="/join/contact">お問合せフォーム</Link>
          よりご質問ください。
        </p>
        <div className={styles.actions} style={{ marginTop: 12 }}>
          <Link className={styles.secondary} href="/join/form">区分選択に戻る</Link>
        </div>
      </section>
    </main>
  );
}
