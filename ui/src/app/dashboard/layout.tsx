import type { Metadata } from "next";
import Link from "next/link";
import { PgsLogo } from "@/components/home/PgsLogo";
import { SectionNav, Sidebar } from "@/components/dashboard/Sidebar";
import { SignOutButton } from "@/components/dashboard/SignOutButton";
import { getSessionUser } from "@/lib/auth/session";

export const metadata: Metadata = {
  title: "Admin dashboard — PGS Search",
};

const ROLE_LABEL = { admin: "Administrator", analyst: "Analyst" } as const;

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await getSessionUser();
  const initials = (user?.name ?? "?")
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100 lg:flex">
      <Sidebar />

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
          <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
            <Link
              href="/"
              aria-label="PGS Search home"
              className="shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 lg:hidden"
            >
              <PgsLogo size="small" />
            </Link>
            <div className="hidden min-w-0 sm:block">
              <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">Admin dashboard</p>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">Crawling, indexing and system health</p>
            </div>

            <div className="ml-auto flex items-center gap-3">
              {user && (
                <div className="flex items-center gap-2.5">
                  <span
                    aria-hidden
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white"
                  >
                    {initials}
                  </span>
                  <div className="hidden leading-tight sm:block">
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{user.name}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{ROLE_LABEL[user.role] ?? user.role}</p>
                  </div>
                  <span className="sr-only sm:hidden">
                    Signed in as {user.name}, {ROLE_LABEL[user.role] ?? user.role}
                  </span>
                </div>
              )}
              <SignOutButton />
            </div>
          </div>
          <SectionNav />
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
