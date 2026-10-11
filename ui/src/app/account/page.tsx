import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { TopNav } from "@/components/layout/TopNav";
import { AccountPanel } from "@/components/account/AccountPanel";
import { apiFetch } from "@/lib/api/server";
import { isHistoryPage } from "@/lib/api/types";
import { getUser, getUserToken } from "@/lib/auth/user-session";

export const metadata: Metadata = { title: "My account — PGS Search" };

const HISTORY_LIMIT = 50;

export default async function AccountPage() {
  const user = await getUser();
  if (!user) redirect("/signin?next=/account");

  const token = await getUserToken();
  const history = await apiFetch("/api/v1/account/history", isHistoryPage, {
    token: token ?? undefined,
    searchParams: { limit: HISTORY_LIMIT },
  });

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <TopNav />
      <AccountPanel
        user={user}
        initialHistory={history.ok ? history.data.items : []}
        hasMore={history.ok && history.data.next_before !== null}
      />
    </div>
  );
}
