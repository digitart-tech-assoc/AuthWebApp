import Link from "next/link";
import { School, UserCheck, MoreHorizontal, Info } from "lucide-react";

export default function JoinFormSelectionPage() {
  return (
    <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
      {/* メインコンテンツ */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          {/* 説明文 */}
          <div className="bg-blue-50/50 border border-blue-100 rounded-2xl p-6 md:p-8 mb-12 space-y-3">
            <p className="text-slate-700 leading-relaxed">
              ご不明点やバグ報告がございましたら、<Link href="/contact" className="font-bold text-emerald-600 hover:text-emerald-700 underline">お問い合わせページ</Link>をご利用ください。
            </p>
            <p className="text-sm text-slate-600 flex items-start gap-2">
              <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              お問い合わせフォームが動作しない場合は、aoyama.tech.exe@gmail.com までご連絡ください。
            </p>
          </div>

          {/* カードグリッド */}
          <div className="grid gap-6 md:grid-cols-3">
            {/* 在学生 */}
            <Link href="/join/form/aoyama-student" className="group">
              <div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <School className="w-6 h-6 text-emerald-600" />
                  </div>
                  <svg className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">在学生</h3>
                <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                  青山学院大学に現在在学中の方向けです。学生番号から学内メールを自動補完します。
                </p>
                <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">青山学院大学</div>
              </div>
            </Link>

            {/* 入学見込み */}
            <Link href="/join/form/prospective-student" className="group">
              <div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <UserCheck className="w-6 h-6 text-blue-600" />
                  </div>
                  <svg className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">入学見込み</h3>
                <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                  青山学院大学への入学が決定されている方向けです。メール認証で仮入会できます。
                </p>
                <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">入学予定者</div>
              </div>
            </Link>

            {/* その他 */}
            <Link href="/join/form/other" className="group">
              <div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-slate-100 to-gray-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <MoreHorizontal className="w-6 h-6 text-slate-600" />
                  </div>
                  <svg className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">その他</h3>
                <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                  上記以外の方向け。詳細をご確認のうえ、お問い合わせください。
                </p>
                <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">詳細確認</div>
              </div>
            </Link>
          </div>

          {/* 戻るボタン */}
          <div className="mt-12 text-center">
            <Link href="/join" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-100 border border-slate-300 text-slate-900 font-semibold hover:bg-slate-50 hover:border-slate-400 transition-all">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
              </svg>
              入会・案内ページに戻る
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

