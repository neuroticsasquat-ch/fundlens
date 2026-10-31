import { describe, expect, it } from "vitest";
import { RACES } from "../test/fixtures";
import { officeLabel, raceLabel, stateName } from "./states";

describe("race labels", () => {
  it("labels the five fixture races within their office", () => {
    expect(RACES.map(raceLabel)).toEqual([
      "President",
      "Maryland",
      "Nebraska special",
      "Maryland 5th",
      "Maryland 8th",
    ]);
  });

  it("labels an at-large district, a territory's delegate and the teens", () => {
    const house = { office: "H" as const, is_special: false };
    expect(raceLabel({ ...house, state: "AK", district: "00" })).toBe("Alaska at-large");
    expect(raceLabel({ ...house, state: "PR", district: "00" })).toBe("Puerto Rico at-large");
    expect(raceLabel({ ...house, state: "NY", district: "12" })).toBe("New York 12th");
    expect(raceLabel({ ...house, state: "TX", district: "22" })).toBe("Texas 22nd");
    expect(raceLabel({ ...house, state: "CA", district: "01", is_special: true })).toBe(
      "California 1st special",
    );
  });

  it("names states, falls back to the code and names offices", () => {
    expect(stateName("US")).toBe("United States");
    expect(stateName("ZZ")).toBe("ZZ");
    expect(officeLabel("S")).toBe("Senate");
  });
});
