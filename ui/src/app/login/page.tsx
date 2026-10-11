import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PgsLogo } from "@/components/home/PgsLogo";
import { LoginForm } from "@/components/auth/LoginForm";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export const metadata: Metadata = {
  title: "Sign in — PGS Search",
};

export default function LoginPage() {
  return (
    // font-sans: same Geist font as the rest of the site (the body falls back to Arial).
    <div className="relative flex min-h-screen flex-col items-center justify-center gap-8 bg-white px-6 font-sans dark:bg-slate-950">
      <div className="absolute right-4 top-4 sm:right-6">
        <ThemeToggle />
      </div>
      <Link
        href="/"
        aria-label="PGS Search home"
        className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <PgsLogo size="small" />
      </Link>
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 p-6 shadow-sm dark:border-slate-800">
        <h1 className="mb-1 text-lg font-semibold text-slate-900 dark:text-slate-100">Sign in</h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          Access the PGS Search dashboard and geo tagging tools.
        </p>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
