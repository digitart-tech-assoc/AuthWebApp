import styles from "../join/join.module.css";

export default function ContactPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>お問い合わせフォーム</h1>
        <p className={styles.lead}>入力項目は要件どおりに配置したモックです。実送信先は未接続です。</p>
      </section>

      <section className={styles.card}>
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>連絡先（メールアドレス）<span className={styles.required}>*</span></label>
            <input className={styles.input} type="email" placeholder="返信に使用するメールアドレス" required />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>氏名（ニックネーム可）<span className={styles.required}>*</span></label>
            <input className={styles.input} placeholder="例: 田中 / たなか123" required />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>所属</label>
            <input className={styles.input} placeholder="例: 青山学院大学 理工学部" />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>件名</label>
            <input className={styles.input} placeholder="お問い合わせの件名" />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>本文</label>
            <textarea className={styles.textarea} placeholder="お問い合わせ内容をご記入ください" />
          </div>

          <div className={styles.actions}>
            <button type="button" className={styles.primary}>送信（モック）</button>
          </div>
        </form>
      </section>
    </main>
  );
}
