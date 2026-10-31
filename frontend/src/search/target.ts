import type { SearchKind, SearchResult } from "../api/client";

/** The SPA route of a race's slug (`2024/senate/NE-special` → `/race/2024/senate/NE?special=1`). */
export function raceRoute(slug: string): string {
  return slug.endsWith("-special")
    ? `/race/${slug.slice(0, -"-special".length)}?special=1`
    : `/race/${slug}`;
}

/** The route a search hit opens. A race's `aliases` is its slug (`gold.search_entity`). */
export function searchTarget(result: SearchResult): string {
  switch (result.kind) {
    case "race":
      return raceRoute(result.aliases ?? "");
    case "candidate":
      return `/candidate/${result.id}`;
    case "committee":
      return `/committee/${result.id}`;
    case "donor":
      return `/donor/${result.id}`;
  }
}

/** The dimmed second line of a hit: its aliases, except a race's, which is only its slug. */
export function searchAliases(result: SearchResult): string | null {
  return result.kind === "race" ? null : result.aliases;
}

export const KIND_LABELS: Record<SearchKind, string> = {
  race: "Races",
  candidate: "Candidates",
  committee: "Committees",
  donor: "Donors",
};

const KIND_ORDER: SearchKind[] = ["race", "candidate", "committee", "donor"];

export type SearchGroup = {
  kind: SearchKind;
  label: string;
  /** Each hit with its position in the API's list, which is best first across every kind. */
  hits: { result: SearchResult; index: number }[];
};

/** Hits grouped by kind in display order, empty groups left out, each in the API's order. */
export function groupByKind(results: SearchResult[]): SearchGroup[] {
  return KIND_ORDER.map((kind) => ({
    kind,
    label: KIND_LABELS[kind],
    hits: results.flatMap((result, index) => (result.kind === kind ? [{ result, index }] : [])),
  })).filter((group) => group.hits.length > 0);
}
