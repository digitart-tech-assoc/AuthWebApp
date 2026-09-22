import Link from "next/link";

export default function NonMemberPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8 pb-16 sm:px-6 sm:py-12 sm:pb-20">
      <section className="mb-6 rounded-2xl border border-slate-200 bg-gradient-to-b from-indigo-500/5 to-white/60 p-6 shadow-sm sm:p-8 md:p-10">
        <div className="flex flex-col items-stretch justify-between gap-6 md:flex-row">
          <div>
            <h1 className="mb-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Digitart テクノロジー愛好会へようこそ</h1>
            <p className="my-1.5 mb-3 text-sm font-medium text-slate-500 sm:text-base">青山学院大学の学生による、学びと交流のコミュニティ</p>
            <p className="m-0 text-sm leading-relaxed text-slate-600 sm:text-base">テクノロジーに興味がある学生が集い、ワークショップやハッカソン、勉強会を開催しています。興味のある方は仮入会から参加してください。</p>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link className="inline-flex h-11 items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-5 text-sm font-bold text-white shadow-sm transition-all hover:brightness-105 hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 no-underline" href="/join/form">
                入会フォームへ
              </Link>
              <Link className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 no-underline" href="/contact">
                お問い合わせ
              </Link>
            </div>
          </div>

          <div className="flex w-full flex-col items-start rounded-xl border border-slate-200 bg-white p-5 shadow-sm md:w-80">
            <div className="mb-2 inline-flex items-center rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 px-2.5 py-1 text-xs font-semibold text-white">メンバー特典</div>
            <h3 className="mb-2 text-base font-semibold text-slate-900">イベント参加・Discord招待</h3>
            <p className="m-0 mb-4 text-sm leading-relaxed text-slate-600">入会後、コミュニティ限定イベントや資料、Discordでの交流に参加できます。</p>
            <div className="mt-auto w-full sm:w-auto">
              <Link className="inline-flex h-10 w-full items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 no-underline sm:w-auto" href="/join/form">今すぐ仮入会</Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
