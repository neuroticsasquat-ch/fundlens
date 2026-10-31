import { useEffect } from "react";
import { useLocation, useSearchParams } from "react-router";
import { parseCycle } from "../shell/cycleTarget";

// A candidate's or committee's page lists every cycle; the cycle switcher sends it to
// `#cycle-{c}` (spec NEU-2043 §4.2), the id of that cycle's totals row.
const CYCLE_HASH = /^#cycle-(\d+)$/;

/**
 * The cycle the page's per-cycle sections show, and how to show another. The page's own picker
 * sets `?cycle=`; otherwise the switcher's `#cycle-{c}`; otherwise `cycles[0]`, the newest. A
 * cycle the page does not have is ignored.
 */
export function useShownCycle(cycles: number[]): [number | undefined, (cycle: number) => void] {
  const [search, setSearch] = useSearchParams();
  const { hash } = useLocation();
  const wanted = [
    parseCycle(search.get("cycle") ?? undefined),
    parseCycle(CYCLE_HASH.exec(hash)?.[1]),
  ];
  const shown = wanted.find((cycle) => cycle !== undefined && cycles.includes(cycle)) ?? cycles[0];
  const show = (cycle: number) =>
    setSearch({ cycle: String(cycle) }, { replace: true, preventScrollReset: true });
  return [shown, show];
}

/** Scrolls to the element the URL's hash names, on load and whenever the hash changes. */
export function useScrollToHash() {
  const { hash } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView();
  }, [hash]);
}
