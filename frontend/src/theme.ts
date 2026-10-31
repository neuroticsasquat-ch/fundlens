import { createTheme } from "@mantine/core";

// Mantine's defaults, spec §8 as amended by NEU-2043: no bespoke palette or webfont.
export const theme = createTheme({ primaryColor: "blue", defaultRadius: "sm" });

/** A party's colour as a Mantine token, for `c`/`color` props; never the primary colour's job. */
export const PARTY_COLOURS = { DEM: "blue.6", REP: "red.6", other: "gray.6" } as const;

export type PartyColourKey = keyof typeof PARTY_COLOURS;

/** The `PARTY_COLOURS` key for an FEC party code (`DEM`, `REP`, anything else). */
export function partyKey(party: string | null): PartyColourKey {
  return party === "DEM" || party === "REP" ? party : "other";
}

/** The `PARTY_COLOURS` entry for an FEC party code (`DEM`, `REP`, anything else). */
export function partyColour(party: string | null): string {
  return PARTY_COLOURS[partyKey(party)];
}
