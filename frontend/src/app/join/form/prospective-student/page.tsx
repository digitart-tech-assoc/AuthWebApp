import Link from "next/link";
import styles from "../../../join/join.module.css";

export default function ProspectiveStudentFormPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>入会フォーム（青山学院大学入学見込み）</h1>
        <p className={styles.lead}>モック画面です。実送信は未接続です。</p>
      </section>

      <section className={styles.card}>
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>氏名<span className={styles.required}>*</span></label>
            <input className={styles.input} placeholder="例: 山田 花子" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>メールアドレス<span className={styles.required}>*</span></label>
            <input className={styles.input} type="email" placeholder="example@mail.com" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>入学予定年度</label>
            <input className={styles.input} placeholder="例: 2027年度" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>自己紹介</label>
            <textarea className={styles.textarea} placeholder="興味分野など" />
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.primary}>送信（モック）</button>
            <Link className={styles.secondary} href="/join/form">区分選択に戻る</Link>
          </div>
        </form>
      </section>
    </main>
  );
}
