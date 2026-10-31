// The one place money, counts and dates are formatted (spec NEU-2043 §6.4): full dollars in
// tables, compact in tiles and on axes.

export const DASH = "—";

const whole = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

// U+2212, not a hyphen, so a negative lines up with the digits.
const signed = (v: number, digits: string) => (v < 0 ? `−$${digits}` : `$${digits}`);

/** `$1,234,567`; a refund-heavy total is `−$1,200`; `null` is a dash. */
export function money(v: number | null | undefined): string {
  if (v == null) return DASH;
  return signed(v, whole.format(Math.abs(v)));
}

/** `$1.2M`, `$54.8K`, `$975`. */
export function moneyCompact(v: number | null | undefined): string {
  if (v == null) return DASH;
  return Math.abs(v) < 1000 ? money(v) : signed(v, compact.format(Math.abs(v)));
}

/** `1,234`. */
export function count(v: number | null | undefined): string {
  return v == null ? DASH : whole.format(v);
}

/** The date part of an ISO timestamp or date: `2024-11-03`. */
export function isoDate(v: string | null | undefined): string {
  return v ? v.slice(0, 10) : DASH;
}
