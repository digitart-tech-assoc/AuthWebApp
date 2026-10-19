// 役割: 画面に表示するエラー文言
// Backend から返された detail・errors などの文言は表示せず、Frontend で定めた固定文言を表示する
// （docs/logging-and-errors.md §3.3）。エラーの詳細は Backend のログで確認する。

/** HTTP ステータスごとの固定文言。該当しないステータスには default を使う */
export type StatusMessages = { default: string } & Partial<Record<number, string>>;

export function messageForStatus(status: number, messages: StatusMessages): string {
  return messages[status] ?? messages.default;
}

/** 画面に表示してよい固定文言を持つエラー（クライアント側のコードで送出する） */
export class DisplayableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DisplayableError";
  }
}

/** 画面に表示する文言を返す。固定文言を持つエラー以外（通信エラー等）には fallback を返す */
export function displayMessage(error: unknown, fallback: string): string {
  return error instanceof DisplayableError ? error.message : fallback;
}

/**
 * Server Action の結果。本番環境では Server Action から送出したエラーのメッセージはクライアントに渡らないため、
 * 想定内のエラーは送出せず、固定文言を値として返す。
 */
export type ActionResult<T> = { ok: true; data: T } | { ok: false; error: string };
