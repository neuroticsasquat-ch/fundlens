// FEC's committee codes (`cm`'s CMTE_TP and CMTE_DSGN) as words, and the conduits by name.

const TYPES: Record<string, string> = {
  C: "Communication cost",
  D: "Delegate committee",
  E: "Electioneering communication",
  H: "House campaign",
  I: "Independent expenditor",
  N: "PAC, nonqualified",
  O: "Super PAC",
  P: "Presidential campaign",
  Q: "PAC, qualified",
  S: "Senate campaign",
  U: "Single-candidate independent expenditure",
  V: "Hybrid PAC, nonqualified",
  W: "Hybrid PAC, qualified",
  X: "Party, nonqualified",
  Y: "Party, qualified",
  Z: "National party nonfederal account",
};

const DESIGNATIONS: Record<string, string> = {
  A: "Authorized by a candidate",
  B: "Lobbyist/registrant PAC",
  D: "Leadership PAC",
  J: "Joint fundraiser",
  P: "Principal campaign committee",
  U: "Unauthorized",
};

/** "Super PAC" for `O`; an unknown code is shown as itself, a missing one as null. */
export function committeeType(code: string | null): string | null {
  return code === null ? null : (TYPES[code] ?? code);
}

/** "Leadership PAC" for `D`; an unknown code is shown as itself, a missing one as null. */
export function committeeDesignation(code: string | null): string | null {
  return code === null ? null : (DESIGNATIONS[code] ?? code);
}

// The conduits the pipeline flags (src/fundlens/fec/conduits.csv), named as people know them.
const CONDUITS: Record<string, string> = { C00401224: "ActBlue", C00694323: "WinRed" };

/** "ActBlue" for its committee id; any other conduit by its id. */
export function conduitName(committeeId: string): string {
  return CONDUITS[committeeId] ?? committeeId;
}
