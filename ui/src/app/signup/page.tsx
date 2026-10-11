import Link from "next/link";
import { Suspense } from "react";
import { PgsLogo } from "@/components/home/PgsLogo";
import { AccountForm } from "@/components/account/AccountForm";

export default function Page() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-white px-6 dark:bg-slate-950">
      <Link href="/">
        <PgsLogo size="small" />
      </Link>
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 p-6 shadow-sm dark:border-slate-800">
        <h1 className="mb-1 text-lg font-semibold text-slate-900 dark:text-slate-100">Create an account</h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          Your searches are saved to your history. You can turn that off or delete it any time.
        </p>
        <Suspense>
          <AccountForm mode="signup" />
        </Suspense>
      </div>
      <Link href="/login" className="text-xs text-slate-500 hover:underline dark:text-slate-400">
        Administrator sign in
      </Link>
    </div>
  );
}
