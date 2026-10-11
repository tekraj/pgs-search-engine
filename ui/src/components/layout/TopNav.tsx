import Link from "next/link";
import { LayoutDashboard, MapPinned, UserRound } from "lucide-react";
import { getSessionUser } from "@/lib/auth/session";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { PgsLogo } from "@/components/home/PgsLogo";
import { getUser } from "@/lib/auth/user-session";

// hideBrand: for pages that already show the logo right below (search), so
// "PGS Search" doesn't appear twice.
export async function TopNav({ hideBrand = false }: { hideBrand?: boolean }) {
  const [user, member] = await Promise.all([getSessionUser(), getUser()]);

  return (
    <header className="flex items-center justify-between gap-3 px-4 py-4 text-sm sm:gap-4 sm:px-6">
      {hideBrand ? (
        <span aria-hidden />
      ) : (
        <Link
          href="/"
          aria-label="PGS Search home"
          className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <PgsLogo size="nav" />
        </Link>
      )}
      <nav className="flex items-center gap-3 text-slate-600 sm:gap-5 dark:text-slate-300">
        <ThemeToggle />
        <Link href="/map" aria-label="Geo Explorer" className="flex items-center gap-1.5 hover:underline">
          <MapPinned className="h-4 w-4" aria-hidden />
          {/* Icon only on phones, so the bar fits on one line. */}
          <span className="hidden sm:inline">Geo Explorer</span>
        </Link>
        {user ? (
          <Link href="/dashboard" aria-label="Dashboard" className="flex items-center gap-1.5 hover:underline">
            <LayoutDashboard className="h-4 w-4" aria-hidden />
            {/* Icon only on phones (with the theme switch the bar is full). */}
            <span className="hidden sm:inline">Dashboard</span>
          </Link>
        ) : null}
        {member ? (
          <Link href="/account" className="flex items-center gap-1.5 hover:underline">
            <UserRound className="h-4 w-4" />
            {member.display_name || member.email}
          </Link>
        ) : null}
        {user ? (
          <span className="hidden rounded-full bg-slate-800 px-3 py-1.5 text-xs font-medium text-white sm:inline-block dark:bg-slate-100 dark:text-slate-900">
            {user.username}
          </span>
        ) : !member ? (
          <>
            <Link href="/signin" className="hover:underline">
              Sign in
            </Link>
            <Link
              href="/signup"
              className="rounded-full bg-blue-600 px-4 py-1.5 font-medium text-white hover:bg-blue-700"
            >
              Sign up
            </Link>
          </>
        ) : null}
      </nav>
    </header>
  );
}
