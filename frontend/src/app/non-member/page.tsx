import Link from "next/link";
import styles from "../join/join.module.css";

export default function NonMemberPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>Digitartテクノロジー愛好会へようこそ</h1>
        <p className={styles.lead}>thanks for visiting Digitartテクノロジー愛好会!!</p>
        <p className={styles.lead}>
          Digitartテクノロジー愛好会は青山学院大学の学生団体です。テクノロジーに興味がある青山学院大学の学生であれば誰でも入会の手続きができます。
          入会を希望する方は、こちらから仮会員として参加してください。当会の活動内容はホームページに記載しております。その他、お問い合わせのある方はフォームよりご質問ください。
        </p>
        <div className={styles.actions} style={{ marginTop: 14 }}>
          <Link className={styles.primary} href="/join/form">
            入会フォームへ
          </Link>
          <Link className={styles.secondary} href="/contact">
            お問い合わせフォーム
          </Link>
        </div>
      </section>
    </main>
  );
}
