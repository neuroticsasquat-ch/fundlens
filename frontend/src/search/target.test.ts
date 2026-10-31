import { describe, expect, it } from "vitest";
import type { SearchResult } from "../api/client";
import { groupByKind, raceRoute, searchTarget } from "./target";

const hit = (
  kind: SearchResult["kind"],
  id: string,
  aliases: string | null = null,
): SearchResult => ({
  kind,
  id,
  name: id,
  aliases,
  score: 0.5,
});

describe("searchTarget", () => {
  it("opens each kind's page", () => {
    expect(searchTarget(hit("race", "2024-S-MD-00", "2024/senate/MD"))).toBe(
      "/race/2024/senate/MD",
    );
    expect(searchTarget(hit("candidate", "H4MD05106"))).toBe("/candidate/H4MD05106");
    expect(searchTarget(hit("committee", "C00800106"))).toBe("/committee/C00800106");
    expect(searchTarget(hit("donor", "d-1"))).toBe("/donor/d-1");
  });

  it("turns a special race's slug suffix into the query the race route takes", () => {
    expect(searchTarget(hit("race", "2024-S-NE-00-special", "2024/senate/NE-special"))).toBe(
      "/race/2024/senate/NE?special=1",
    );
    expect(raceRoute("2024/house/MD-05")).toBe("/race/2024/house/MD-05");
  });
});

describe("groupByKind", () => {
  it("orders groups races first, keeps the API's order within one and drops empty kinds", () => {
    const results = [hit("committee", "a"), hit("race", "b"), hit("committee", "c")];

    expect(
      groupByKind(results).map((g) => [
        g.label,
        g.hits.map(({ result, index }) => [result.id, index]),
      ]),
    ).toEqual([
      ["Races", [["b", 1]]],
      [
        "Committees",
        [
          ["a", 0],
          ["c", 2],
        ],
      ],
    ]);
  });
});
