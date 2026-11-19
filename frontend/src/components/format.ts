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

/**
 * A reported total's figure: `money`, but a measure FEC's file for the cycle lacks is "not
 * reported", never 0 and never a dash (every-FEC-dollar spec §4.7).
 */
export function reportedMoney(v: number | null | undefined): string {
  return v == null ? "not reported" : money(v);
}

/** `$1.2M`, `$54.8K`, `$975`. */
export function moneyCompact(v: number | null | undefined): string {
  if (v == null) return DASH;
  return Math.abs(v) < 1000 ? money(v) : signed(v, compact.format(Math.abs(v)));
}

const percentage = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** A share between 0 and 1 as `62.9%`. */
export function percent(v: number | null | undefined): string {
  return v == null ? DASH : percentage.format(v);
}

/** `1,234`. */
export function count(v: number | null | undefined): string {
  return v == null ? DASH : whole.format(v);
}

/** The date part of an ISO timestamp or date: `2024-11-03`. */
export function isoDate(v: string | null | undefined): string {
  return v ? v.slice(0, 10) : DASH;
}

const sized = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const UNITS = ["bytes", "kB", "MB", "GB", "TB"];

/** A file's size in decimal units: `512 bytes`, `9.9 kB`, `1.2 GB`. */
export function fileSize(v: number | null | undefined): string {
  if (v == null) return DASH;
  let size = v;
  let unit = 0;
  while (size >= 1000 && unit < UNITS.length - 1) {
    size /= 1000;
    unit += 1;
  }
  return `${sized.format(size)} ${UNITS[unit]}`;
}
