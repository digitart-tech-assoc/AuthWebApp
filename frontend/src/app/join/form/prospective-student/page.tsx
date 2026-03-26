import Link from "next/link";
import styles from "../../../join/join.module.css";

export default function ProspectiveStudentFormPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>仮入会フォーム（青山学院大学入学見込み）</h1>
        <p className={styles.lead}>モック画面です。実送信は未接続です。</p>
      </section>

      <section className={styles.card} style={{ marginBottom: 16 }}>
        <h2 className={styles.cardTitle}>入会の流れ</h2>
        <ol style={{ margin: 0, paddingLeft: 18, color: "#475569", lineHeight: 1.6 }}>
          <li>必要事項（氏名、メールアドレス 等）を入力して「送信」を押してください。</li>
          <li>入力したメールアドレス宛に認証パスワード（ワンタイムコード）を送信します。</li>
          <li>メールに届いた認証パスワードをこのページの確認欄に入力して検証してください。</li>
          <li>検証成功後、Discord招待リンクが発行されます。リンクからサーバーに参加してください。</li>
        </ol>
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
            <label className={styles.label}>質問等</label>
            <textarea className={styles.textarea} placeholder="質問、連絡事項等あればご記入ください" />
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
