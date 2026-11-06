// 役割: 大学メール（@aoyama.ac.jp）宛ての認証メールが届かない不具合を案内する。不具合の解消後に削除する

import Link from "next/link";
import { alertWarning, textLink } from "./joinStyles";

export default function UniversityMailNotice() {
  return (
    <div className={`${alertWarning} my-3`}>
      <p>大学のメールサーバーが認証メールを受信できない不具合が報告されています。</p>
      <p>
        一度試しメールが届かなかった場合は
        {/* 入力中のフォームの内容を失わないよう、別タブで開く */}
        <Link href="/contact" target="_blank" rel="noreferrer" className={textLink}>
          お問い合わせフォーム
        </Link>
        にてお声がけください
      </p>
    </div>
  );
}
