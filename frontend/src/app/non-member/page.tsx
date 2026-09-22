import Link from "next/link";

export default function NonMemberPage() {
  return (
    <main className="mx-auto max-w-5xl px-5 py-10 pb-[72px]">
      <section className="mb-[18px] rounded-[14px] border border-slate-900/5 bg-gradient-to-b from-indigo-500/5 to-white/60 p-9 shadow-[0_6px_18px_rgba(15,23,42,0.04)]">
        <div className="flex flex-col items-stretch justify-between gap-5 md:flex-row">
          <div>
            <h1 className="mb-2 text-[26px] leading-normal text-slate-900">Digitart テクノロジー愛好会へようこそ</h1>
            <p className="my-[6px] mb-2.5 font-semibold text-gray-500">青山学院大学の学生による、学びと交流のコミュニティ</p>
            <p className="m-0 leading-[1.7] text-slate-600">テクノロジーに興味がある学生が集い、ワークショップやハッカソン、勉強会を開催しています。興味のある方は仮入会から参加してください。</p>

            <div className="mt-5 flex flex-wrap gap-3">
              <Link className="inline-flex items-center justify-center rounded-[10px] bg-gradient-to-r from-blue-600 to-indigo-600 px-[18px] py-3 text-[15px] font-bold text-white no-underline shadow-[0_6px_18px_rgba(37,99,235,0.14)] transition hover:-translate-y-0.5 hover:brightness-[1.03] hover:shadow-[0_10px_26px_rgba(37,99,235,0.16)]" href="/join/form">
                入会フォームへ
              </Link>
              <Link className="inline-flex items-center justify-center rounded-[10px] border border-slate-900/5 bg-transparent px-3.5 py-2.5 text-sm font-semibold text-slate-900 no-underline transition hover:-translate-y-px hover:bg-slate-900/[0.03]" href="/contact">
                お問い合わせ
              </Link>
            </div>
          </div>

          <div className="flex w-full flex-col items-start rounded-xl border border-slate-900/[0.03] bg-gradient-to-b from-white to-slate-50/70 p-[18px] shadow-[0_8px_30px_rgba(2,6,23,0.06)] md:w-80">
            <div className="mb-2 inline-block rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 px-2.5 py-1.5 text-xs font-bold text-white">メンバー特典</div>
            <h3 className="mb-2 text-base font-semibold text-slate-900">イベント参加・Discord招待</h3>
            <p className="m-0 mb-3 text-sm leading-[1.7] text-slate-600">入会後、コミュニティ限定イベントや資料、Discordでの交流に参加できます。</p>
            <div className="mt-3">
              <Link className="inline-flex items-center justify-center rounded-[10px] border border-slate-900/5 bg-transparent px-3.5 py-2.5 text-sm font-semibold text-slate-900 no-underline transition hover:-translate-y-px hover:bg-slate-900/[0.03]" href="/join/form">今すぐ仮入会</Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
