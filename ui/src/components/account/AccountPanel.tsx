"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Trash2, X } from "lucide-react";
import type { HistoryEntry, UserProfile } from "@/lib/api/types";

async function call(url: string, method: string, body?: unknown): Promise<string | null> {
  try {
    const res = await fetch(url, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (res.ok) return null;
    const data = await res.json().catch(() => ({}));
    return data.error ?? "Something went wrong.";
  } catch {
    return "The server is unreachable.";
  }
}

export function AccountPanel({
  user,
  initialHistory,
  hasMore,
}: {
  user: UserProfile;
  initialHistory: HistoryEntry[];
  hasMore: boolean;
}) {
  const router = useRouter();
  const [history, setHistory] = useState(initialHistory);
  const [saveHistory, setSaveHistory] = useState(user.save_history);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [password, setPassword] = useState("");

  async function toggle(enabled: boolean) {
    setError(null);
    const failure = await call("/api/account/settings", "PATCH", { save_history: enabled });
    if (failure) setError(failure);
    else setSaveHistory(enabled);
  }

  async function remove(id: number) {
    setError(null);
    const failure = await call(`/api/account/history/${id}`, "DELETE");
    if (failure) setError(failure);
    else setHistory((rows) => rows.filter((row) => row.id !== id));
  }

  async function clearAll() {
    setError(null);
    const failure = await call("/api/account/history", "DELETE");
    if (failure) setError(failure);
    else setHistory([]);
  }

  async function signOut() {
    await call("/api/account/logout", "POST");
    router.push("/");
    router.refresh();
  }

  async function deleteAccount(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const failure = await call("/api/account/delete", "POST", { password });
    if (failure) {
      setError(failure);
      return;
    }
    router.push("/");
    router.refresh();
  }

  const button =
    "rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800";

  return (
    <div className="mx-auto max-w-2xl space-y-8 px-6 py-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            {user.display_name || user.email}
          </h1>
          {user.display_name ? <p className="text-sm text-slate-500 dark:text-slate-400">{user.email}</p> : null}
        </div>
        <button type="button" onClick={signOut} className={button}>
          Sign out
        </button>
      </header>

      {error ? (
        <p role="alert" className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
          {error}
        </p>
      ) : null}

      <section>
        <label className="flex items-center gap-3 text-sm text-slate-700 dark:text-slate-300">
          <input
            type="checkbox"
            checked={saveHistory}
            onChange={(e) => toggle(e.target.checked)}
            className="h-4 w-4"
          />
          Save my searches to my history
        </label>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Search history</h2>
          {history.length > 0 ? (
            <button type="button" onClick={clearAll} className={`${button} flex items-center gap-1.5`}>
              <Trash2 className="h-4 w-4" aria-hidden /> Clear all
            </button>
          ) : null}
        </div>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {saveHistory ? "Nothing here yet. Your searches will appear here." : "History is off."}
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {history.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <Link
                    href={`/search?${new URLSearchParams({ q: row.query })}`}
                    className="block truncate text-sm text-blue-700 hover:underline dark:text-blue-400"
                  >
                    {row.query}
                  </Link>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {new Date(row.searched_at).toLocaleString()} · {row.result_count} result
                    {row.result_count === 1 ? "" : "s"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => remove(row.id)}
                  aria-label={`Remove “${row.query}” from history`}
                  className="shrink-0 rounded p-1 text-slate-400 hover:text-rose-600"
                >
                  <X className="h-4 w-4" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
        {hasMore ? (
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">Showing your most recent searches.</p>
        ) : null}
      </section>

      <section className="border-t border-slate-200 pt-6 dark:border-slate-800">
        <h2 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">Delete account</h2>
        {confirmDelete ? (
          <form onSubmit={deleteAccount} className="flex flex-wrap items-center gap-2">
            <input
              type="password"
              required
              autoComplete="current-password"
              placeholder="Confirm your password"
              aria-label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-slate-200 bg-transparent px-3 py-1.5 text-sm dark:border-slate-700"
            />
            <button type="submit" className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700">
              Delete my account and history
            </button>
            <button type="button" onClick={() => setConfirmDelete(false)} className={button}>
              Cancel
            </button>
          </form>
        ) : (
          <button type="button" onClick={() => setConfirmDelete(true)} className={button}>
            Delete my account…
          </button>
        )}
      </section>
    </div>
  );
}
