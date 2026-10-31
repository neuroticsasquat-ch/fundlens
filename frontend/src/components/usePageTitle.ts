import { useEffect } from "react";

/** Sets `document.title` to "{title} · fundlens", or "fundlens" with no title (the home page). */
export function usePageTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} · fundlens` : "fundlens";
  }, [title]);
}
