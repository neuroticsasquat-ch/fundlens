import { within } from "@testing-library/react";

/** The reported panel's figures in `region`, each label to its figure, in the order shown. */
export function figures(region: HTMLElement): [string | null, string | null][] {
  const terms = within(region).getAllByRole("term");
  const values = within(region).getAllByRole("definition");
  return terms.map((term, i) => [term.textContent, values[i].textContent]);
}
