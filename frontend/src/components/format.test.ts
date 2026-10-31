import { describe, expect, it } from "vitest";
import { count, DASH, isoDate, money, moneyCompact } from "./format";

describe("format", () => {
  it("writes full dollars, a minus sign for negatives and a dash for nothing", () => {
    expect(money(1234567)).toBe("$1,234,567");
    expect(money(-1200)).toBe("−$1,200");
    expect(money(0)).toBe("$0");
    expect(money(null)).toBe(DASH);
  });

  it("writes compact dollars to one decimal above a thousand", () => {
    expect(moneyCompact(1_200_000)).toBe("$1.2M");
    expect(moneyCompact(54775)).toBe("$54.8K");
    expect(moneyCompact(2244775)).toBe("$2.2M");
    expect(moneyCompact(975)).toBe("$975");
    expect(moneyCompact(-54775)).toBe("−$54.8K");
    expect(moneyCompact(undefined)).toBe(DASH);
  });

  it("writes counts with separators and dates as their ISO date part", () => {
    expect(count(1234)).toBe("1,234");
    expect(count(null)).toBe(DASH);
    expect(isoDate("2024-11-03T08:00:00Z")).toBe("2024-11-03");
    expect(isoDate("2024-11-02")).toBe("2024-11-02");
    expect(isoDate(null)).toBe(DASH);
  });
});
