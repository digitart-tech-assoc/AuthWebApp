import Link from "next/link";
import { Zap, Check, Plus, Users, Mail, ChevronRight } from "lucide-react";

export default function JoinGuidePage() {
	return (
		<main className="bg-slate-50 text-slate-900 font-sans min-h-screen">

			{/* メインコンテンツ */}
			<section className="py-16 px-6">
				<div className="max-w-5xl mx-auto space-y-12">


					{/* カードグリッド */}
					<div className="grid gap-6 md:grid-cols-3">
						{/* 仮入会 */}
						<Link href="/join/form?mode=temporary" className="group">
							<div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
								<div className="flex items-start justify-between mb-4">
										<div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
											<Plus className="w-6 h-6 text-emerald-600" />
										</div>
									<ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" />
								</div>
								<h3 className="text-xl font-bold text-slate-900 mb-2">仮入会（メール認証）</h3>
								<p className="text-sm text-slate-600 mb-6 leading-relaxed">
									メール認証で仮登録できます。まずはこちらを選んでください。
								</p>
								<div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">仮入会</div>
							</div>
						</Link>

						{/* 本入会 */}
						<Link href="/join/member" className="group">
							<div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
								<div className="flex items-start justify-between mb-4">
										<div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
											<Check className="w-6 h-6 text-emerald-600" />
										</div>
									<ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" />
								</div>
								<h3 className="text-xl font-bold text-slate-900 mb-2">本入会（詳細フォーム）</h3>
								<p className="text-sm text-slate-600 mb-6 leading-relaxed">
									本登録用の詳細フォームです。必要書類や情報を準備してお進みください。
								</p>
								<div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">本入会</div>
							</div>
						</Link>

						{/* ロール管理
						<Link href="/roles" className="group">
							<div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
								<div className="flex items-start justify-between mb-4">
                                        <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                                        	<Users className="w-6 h-6 text-emerald-600" />
                                        </div>
									<ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" />
								</div>
								<h3 className="text-xl font-bold text-slate-900 mb-2">ロール管理</h3>
								<p className="text-sm text-slate-600 mb-6 leading-relaxed">
									member / OBOG 権限保持者はこちらからロール管理ページへアクセスしてください。
								</p>
								<div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">会員向け</div>
							</div>
						</Link> */}

						{/* お問い合わせ */}
						<Link href="/contact" className="group">
							<div className="bg-white rounded-2xl border border-slate-100 p-8 h-full shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 hover:border-emerald-200">
								<div className="flex items-start justify-between mb-4">
                                        <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                                        	<Mail className="w-6 h-6 text-emerald-600" />
                                        </div>
									<ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" />
								</div>
								<h3 className="text-xl font-bold text-slate-900 mb-2">お問い合わせ</h3>
								<p className="text-sm text-slate-600 mb-6 leading-relaxed">
									ご質問やご不明な点がありましたら、こちらのフォームからお気軽にお問い合わせください。
								</p>
								<div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">全員対象</div>
							</div>
						</Link>
					</div>

					{/* 非会員向けセクション
					<div className="bg-gradient-to-r from-slate-100 to-slate-50 rounded-2xl border border-slate-200 p-8 md:p-12">
						<div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
							<div className="space-y-3">
								<h2 className="text-2xl font-bold text-slate-900">対象外の方へ</h2>
								<p className="text-slate-600 leading-relaxed">
									当サークルの入会対象外となられた方は、こちらをご確認ください。<br className="hidden md:block" />
									その他ご分からな点がありましたら、お問い合わせフォームよりご連絡ください。
								</p>
							</div>
                                <Link href="/non-member" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white border border-slate-300 text-slate-900 font-semibold hover:bg-slate-50 hover:border-slate-400 transition-all whitespace-nowrap">
                                	詳しく見る
                                	<ChevronRight className="w-4 h-4" />
                                </Link>
						</div>
					</div> */}
				</div>
			</section>
		</main>
	);
}
