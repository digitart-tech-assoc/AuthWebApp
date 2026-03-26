import type { Metadata } from "next";
import { createSupabaseServer } from "@/lib/supabase";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AuthWebApp",
  description: "Discord role management for your server",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const authRequired = process.env.AUTH_REQUIRED !== "false";
  const supabase = await createSupabaseServer();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email ??
    null;

  return (
    <html
      lang="ja"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="w-full border-b border-black/10 bg-white/80 backdrop-blur dark:border-white/10 dark:bg-black/50">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-sm font-semibold tracking-wide">
              AuthWebApp
            </Link>
            <div className="flex items-center gap-2">
              <Link
                href="/roles"
                className="rounded-md px-3 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/10"
              >
                Roles
              </Link>
              {user ? (
                <>
                  {displayName && (
                    <span className="text-sm text-zinc-500 dark:text-zinc-400">
                      {displayName}
                    </span>
                  )}
                  <a
                    href="/api/auth/signout?callbackUrl=%2F"
                    className="rounded-md bg-black px-3 py-1.5 text-sm text-white hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/80"
                  >
                    Logout
                  </a>
                </>
              ) : authRequired ? (
                <a
                  href="/login?callbackUrl=%2Froles"
                  className="rounded-md bg-black px-3 py-1.5 text-sm text-white hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/80"
                >
                  Login
                </a>
              ) : (
                <a
                  href="/login?callbackUrl=%2Froles"
                  className="rounded-md border border-black/15 px-3 py-1.5 text-sm hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
                >
                  Login
                </a>
              )}
            </div>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
