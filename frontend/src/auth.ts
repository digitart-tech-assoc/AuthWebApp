// 役割: Supabase セッションヘルパー（旧 next-auth の auth() を置き換え）
// 後方互換のため一部コンポーネントが参照している可能性がある場合のシム

export { createSupabaseServer as getServerSession } from "@/lib/supabase";