import type { Office, RaceSummary } from "../api/client";

/** FEC state codes: the 50 states, DC, the delegate territories, and `US` for President. */
export const STATE_NAMES: Record<string, string> = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
  DC: "District of Columbia",
  PR: "Puerto Rico",
  GU: "Guam",
  VI: "U.S. Virgin Islands",
  AS: "American Samoa",
  MP: "Northern Mariana Islands",
  US: "United States",
};

/** A state's name; an unknown code is shown as itself. */
export function stateName(code: string): string {
  return STATE_NAMES[code] ?? code;
}

const OFFICE_LABELS: Record<Office, string> = { P: "President", S: "Senate", H: "House" };

/** "President", "Senate" or "House". */
export function officeLabel(office: Office): string {
  return OFFICE_LABELS[office];
}

function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  return `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th"}`;
}

type RaceKey = Pick<RaceSummary, "office" | "state" | "district" | "is_special">;

/** A race within its office: "President", "Nebraska special", "Maryland 5th", "Alaska at-large". */
export function raceLabel({ office, state, district, is_special }: RaceKey): string {
  if (office === "P") return "President";
  const place =
    office === "S"
      ? stateName(state)
      : `${stateName(state)} ${Number(district) === 0 ? "at-large" : ordinal(Number(district))}`;
  return is_special ? `${place} special` : place;
}

const SLUG_OFFICES: Record<string, Office> = { president: "P", senate: "S", house: "H" };

// A race's slug (`gold.race.slug`): `2024/senate/MD`, `2024/house/MD-05`,
// `2024/senate/NE-special`.
const SLUG = /^\d{4}\/(president|senate|house)\/([A-Z]{2})(?:-(\d{2}))?(-special)?$/;

/** A race named from its slug, without the cycle: "Senate · Maryland"; else the slug itself. */
export function raceSlugLabel(slug: string): string {
  const match = SLUG.exec(slug);
  if (!match) return slug;
  const [, segment, state, district = "00", special] = match;
  const office = SLUG_OFFICES[segment];
  if (office === "P") return "President";
  const seat = raceLabel({ office, state, district, is_special: !!special });
  return `${officeLabel(office)} · ${seat}`;
}
