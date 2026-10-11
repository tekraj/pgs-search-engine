import { cn } from "@/lib/cn";

// Single-colour blue wordmark (a lighter blue in dark mode so it stays readable).
export function PgsLogo({ size = "large" }: { size?: "large" | "small" | "nav" }) {
  return (
    <div
      className={cn(
        "select-none font-bold tracking-tight text-blue-700 dark:text-blue-400",
        size === "large" ? "text-[3.5rem] leading-none sm:text-7xl lg:text-8xl" : size === "nav" ? "text-lg" : "text-2xl"
      )}
    >
      PGS Search
    </div>
  );
}
