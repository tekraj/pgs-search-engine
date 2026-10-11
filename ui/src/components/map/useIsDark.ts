import { useSyncExternalStore } from "react";

// Whether the page is in dark mode: the theme chosen in the top bar, stored as
// data-theme on <html>. The map's colors are set from JavaScript, so it can't
// rely on CSS dark: classes.
function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

export function useIsDark(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => document.documentElement.getAttribute("data-theme") === "dark",
    () => false
  );
}
