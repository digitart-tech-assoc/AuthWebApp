import Link from "next/link";
import { Info, Check, Mail, ArrowLeft } from "lucide-react";

export default function OtherApplicantFormPage() {
  return (
    <main className="bg-slate-50 text-slate-900 font-sans min-h-screen">
      {/* ヒーロー部分 */}
      <section className="bg-gradient-to-br from-slate-50 via-white to-amber-50 pt-10 pb-10 md:pt-10 md:pb-10 px-6">
        <div className="max-w-4xl mx-auto text-center space-y-6 md:space-y-8">
          <div className="inline-block">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-amber-200/50 bg-amber-50/50">
              <Info className="w-4 h-4 text-amber-600" />
              <span className="text-sm font-semibold text-amber-700">その他の方へ</span>
            </div>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight">
            <span className="text-slate-900">申し訳ございません</span>
          </h1>

          <p className="text-lg md:text-1xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Digitartテクノロジー愛好会に興味を持ってくださり、ありがとうございます。<br/>
            当団体は現在、青山学院大学の学生のみ入会できます。
          </p>
        </div>
      </section>

      {/* メインコンテンツ */}
      <section className="py-12 px-4">
        <div className="max-w-3xl mx-auto">
          {/* メッセージカード */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6 md:p-8 shadow-sm space-y-6 mb-8">
            <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mt-1">
                <Info className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900 mb-2">入会対象について</h2>
                <p className="text-slate-600 leading-relaxed">
                  Digitartテクノロジー愛好会は、青山学院大学に所属する学生のみ入会対象としています。他大学の学生や卒業生の方、また社会人の方のご入会はお受けしていません。
                </p>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 space-y-4">
              <h3 className="font-bold text-slate-900 flex items-center gap-2">
                <Info className="w-5 h-5 text-blue-600" />
                以下の場合にお力になれるかもしれません
              </h3>
              <ul className="space-y-2 text-slate-600 ml-7">
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-1" />
                  <span>青山学院大学への入学が決定している場合：<Link href="/join/form/prospective-student" className="font-bold text-emerald-600 hover:text-emerald-700">入学見込みフォーム</Link>からお申し込みください</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-1" />
                  <span>ご質問やその他のご相談がある場合：下記のお問い合わせ先までご連絡ください</span>
                </li>
              </ul>
            </div>
          </div>

          {/* お問い合わせセクション */}
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-2xl border border-emerald-200 p-6 md:p-8 space-y-6 mt-6 mb-8">
            <h2 className="text-2xl font-bold text-slate-900">ご質問やご相談はこちら</h2>
            <p className="text-slate-600 leading-relaxed">
              ご不明な点やご質問がございましたら、以下のどちらかからお気軽にお問い合わせください。
            </p>
            
            <div className="grid gap-4 md:grid-cols-2">
              {/* Contactフォーム */}
              <Link href="/contact" className="group">
                <div className="bg-white rounded-xl border border-slate-200 p-6 hover:border-emerald-300 hover:shadow-lg transition-all duration-300 h-full flex flex-col justify-start space-y-3">
                  <div className="flex items-center gap-3 mb-3">
                      <Mail className="w-6 h-6 text-emerald-600" />
                    <h3 className="font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">お問い合わせフォーム</h3>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Webフォームからご質問をお送りいただけます。
                  </p>
                </div>
              </Link>

              {/* メール */}
              <a href="mailto:aoyama.tech.exe@gmail.com" className="group">
                <div className="bg-white rounded-xl border border-slate-200 p-6 hover:border-emerald-300 hover:shadow-lg transition-all duration-300 h-full flex flex-col justify-start space-y-3">
                  <div className="flex items-center gap-3 mb-3">
                    <Mail className="w-6 h-6 text-emerald-600" />
                    <h3 className="font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">メール</h3>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed break-all">
                    aoyama.tech.exe@gmail.com
                  </p>
                </div>
              </a>
            </div>
          </div>

          {/* 戻るボタン */}
          <div className="text-center">
            <Link href="/join/form" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-100 border border-slate-300 text-slate-900 font-semibold hover:bg-slate-50 hover:border-slate-400 transition-all">
              <ArrowLeft className="w-4 h-4" />
              フォーム選択に戻る
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
