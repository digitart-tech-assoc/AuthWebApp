"use client";

import Link from "next/link";
import { card } from "./joinStyles";

interface FormStep5Props {
  studentNumber: string;
  name: string;
}

export default function FormStep5Complete({
  studentNumber,
  name,
}: FormStep5Props) {
  return (
    <div className={card}>
      <div className="px-4 py-8 text-center">
        <div className="mb-4 text-5xl">✅</div>

        <h2 className="mb-3 text-2xl font-bold text-slate-900">
          入会登録完了！
        </h2>

        <p className="mb-6 text-base text-slate-500">
          {name} さん、本会員としての登録が完了しました。
        </p>

        <div className="mb-6 rounded-lg border border-slate-200 bg-slate-50 p-5 text-left">
          <h3 className="mb-2 text-sm font-semibold text-slate-900">
            登録情報
          </h3>
          <p className="my-1 text-sm text-slate-700">
            <strong>学生番号:</strong> {studentNumber}
          </p>
          <p className="my-1 text-sm text-slate-700">
            <strong>名前:</strong> {name}
          </p>
        </div>

        <Link
          href="/contact"
          className="mx-auto flex h-10 w-full max-w-75 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          お問い合わせ
        </Link>
      </div>
    </div>
  );
}
