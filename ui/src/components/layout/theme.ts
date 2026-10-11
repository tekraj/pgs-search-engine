// Light / dark / auto theme. The choice is saved per device (localStorage) and
// applied as data-theme="light" | "dark" on <html>; Tailwind's dark: styles
// follow that attribute (see the @custom-variant in globals.css).

export type ThemeChoice = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "pgs_theme";
const CHANGE_EVENT = "pgs-theme-change";

// Runs in <head> before the first paint (see app/layout.tsx), so the page
// never flashes the wrong theme. In "system" mode it also follows the
// computer's setting live.
export const THEME_INIT_SCRIPT = `(function(){
var k="${THEME_STORAGE_KEY}",d=document.documentElement,m=window.matchMedia("(prefers-color-scheme: dark)");
function c(){try{return localStorage.getItem(k)||"system"}catch(e){return "system"}}
function a(){var t=c();d.setAttribute("data-theme",t==="dark"||(t!=="light"&&m.matches)?"dark":"light")}
a();m.addEventListener("change",function(){if(c()==="system")a()});
})()`;

export function readThemeChoice(): ThemeChoice {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

export function setThemeChoice(choice: ThemeChoice) {
  try {
    if (choice === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
    else window.localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    // Private browsing: the choice applies now but isn't remembered.
  }
  const dark = choice === "dark" || (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

/** Subscribe to theme choice changes (made on this page or in another tab). */
export function subscribeThemeChoice(onChange: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === THEME_STORAGE_KEY) {
      setThemeChoice(readThemeChoice());
      onChange();
    }
  };
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}
