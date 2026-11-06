// 役割: 大学メール（@aoyama.ac.jp）宛ての認証メールが届かない不具合を案内する。不具合の解消後に削除する

import Link from "next/link";
import { alertWarning, textLink } from "./joinStyles";

export default function UniversityMailNotice() {
  return (
    <div className={`${alertWarning} my-3`}>
      <p>大学のメールアドレス宛ての認証メールが、届かない、または大幅に遅れる場合があります。</p>
      <p>
        メールが届かなかった場合は
        {/* 入力中のフォームの内容を失わないよう、別タブで開く */}
        <Link href="/contact" target="_blank" rel="noreferrer" className={textLink}>
          お問い合わせフォーム
        </Link>
        にてお声がけください。
      </p>
    </div>
  );
}
