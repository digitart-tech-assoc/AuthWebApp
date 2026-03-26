import Link from "next/link";
import styles from "../../../join/join.module.css";

export default function AoyamaStudentFormPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>入会フォーム（青山学院大学の学生）</h1>
        <p className={styles.lead}>モック画面です。実送信は未接続です。</p>
      </section>

      <section className={styles.card}>
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>氏名<span className={styles.required}>*</span></label>
            <input className={styles.input} placeholder="例: 山田 太郎" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>メールアドレス<span className={styles.required}>*</span></label>
            <input className={styles.input} type="email" placeholder="example@aoyama.jp" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>学部・学科</label>
            <input className={styles.input} placeholder="例: 社会情報学部 社会情報学科" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>学年</label>
            <select className={styles.select} defaultValue="">
              <option value="" disabled>選択してください</option>
              <option>1年</option>
              <option>2年</option>
              <option>3年</option>
              <option>4年</option>
              <option>大学院</option>
            </select>
          </div>
          <div className={styles.field}>
            <label className={styles.label}>備考</label>
            <textarea className={styles.textarea} placeholder="参加目的など" />
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
