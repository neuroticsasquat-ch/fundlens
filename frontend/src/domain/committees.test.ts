import { describe, expect, it } from "vitest";
import { committeeDesignation, committeeType, conduitName } from "./committees";

describe("committee codes", () => {
  it("names FEC's type and designation codes, and shows an unknown one as itself", () => {
    expect(committeeType("O")).toBe("Super PAC");
    expect(committeeType("S")).toBe("Senate campaign");
    expect(committeeType("?")).toBe("?");
    expect(committeeType(null)).toBeNull();
    expect(committeeDesignation("D")).toBe("Leadership PAC");
    expect(committeeDesignation("P")).toBe("Principal campaign committee");
    expect(committeeDesignation(null)).toBeNull();
  });

  it("names the two conduits, and any other by its id", () => {
    expect(conduitName("C00401224")).toBe("ActBlue");
    expect(conduitName("C00694323")).toBe("WinRed");
    expect(conduitName("C00999999")).toBe("C00999999");
  });
});
