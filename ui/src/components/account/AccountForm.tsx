"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Loader2, Lock, Mail, User } from "lucide-react";

/** Sign in or sign up a public-site user (the admin sign-in is /login). */
export function AccountForm({ mode }: { mode: "signin" | "signup" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Only same-site paths: an absolute ?next= would be an open redirect.
  const requested = searchParams.get("next") ?? "";
  const next =
    requested.startsWith("/") && !requested.startsWith("//") && !requested.includes("\\") ? requested : "/account";

  const signup = mode === "signup";
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(signup ? "/api/account/register" : "/api/account/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signup ? { email, password, display_name: displayName } : { email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error ?? (signup ? "Sign up failed." : "Sign in failed."));
        return;
      }
      router.push(next);
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  const field =
    "flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700";
  const label = "mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300";
  const input = "w-full bg-transparent text-sm outline-none";

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
      {signup ? (
        <div>
          <label htmlFor="display_name" className={label}>
            Name (optional)
          </label>
          <div className={field}>
            <User className="h-4 w-4 text-slate-400" aria-hidden />
            <input
              id="display_name"
              type="text"
              autoComplete="name"
              maxLength={100}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className={input}
            />
          </div>
        </div>
      ) : null}

      <div>
        <label htmlFor="email" className={label}>
          Email
        </label>
        <div className={field}>
          <Mail className="h-4 w-4 text-slate-400" aria-hidden />
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={input}
          />
        </div>
      </div>

      <div>
        <label htmlFor="password" className={label}>
          Password{signup ? " (at least 12 characters)" : ""}
        </label>
        <div className={field}>
          <Lock className="h-4 w-4 text-slate-400" aria-hidden />
          <input
            id="password"
            type="password"
            autoComplete={signup ? "new-password" : "current-password"}
            required
            minLength={signup ? 12 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={input}
          />
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-rose-600">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {signup ? "Create account" : "Sign in"}
      </button>

      <p className="text-center text-xs text-slate-500 dark:text-slate-400">
        {signup ? (
          <>
            Already have an account?{" "}
            <Link href="/signin" className="text-blue-700 hover:underline dark:text-blue-400">
              Sign in
            </Link>
          </>
        ) : (
          <>
            New here?{" "}
            <Link href="/signup" className="text-blue-700 hover:underline dark:text-blue-400">
              Create an account
            </Link>
          </>
        )}
      </p>
    </form>
  );
}
