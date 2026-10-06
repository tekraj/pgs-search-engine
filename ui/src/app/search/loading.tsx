// Shown while a new search loads (Next.js route loading UI).
export default function SearchLoading() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6" role="status" aria-label="Loading results">
      <div className="max-w-2xl space-y-8">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse space-y-2">
            <div className="h-3 w-40 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="h-5 w-3/4 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="h-3 w-full rounded bg-slate-100 dark:bg-slate-900" />
            <div className="h-3 w-5/6 rounded bg-slate-100 dark:bg-slate-900" />
          </div>
        ))}
      </div>
    </div>
  );
}
