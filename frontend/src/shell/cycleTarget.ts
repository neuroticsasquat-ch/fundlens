import type { Location, Params, To } from "react-router";
import { useLocation, useMatches } from "react-router";

/**
 * What a route tells the cycle switcher (spec NEU-2043 §4.2), as its `handle`. A route without
 * one shows the current cycle and switches to the chosen cycle's race index.
 */
export type CycleHandle = {
  /** The route's cycle, shown in the switcher; undefined when the URL has none. */
  cycle?: (params: Params) => number | undefined;
  /** Where picking `cycle` goes from this route. */
  cycleTarget?: (cycle: number, params: Params, location: Location) => To;
};

export const defaultCycleTarget = (cycle: number): To => `/cycles/${cycle}`;

/** A `:cycle` URL segment as a cycle, or undefined when it is not an integer. */
export function parseCycle(value: string | undefined): number | undefined {
  const cycle = Number(value);
  return value && Number.isInteger(cycle) ? cycle : undefined;
}

/** The deepest matched route's cycle, and where picking another cycle should go from it. */
export function useCycleTarget(): {
  cycle: number | undefined;
  target: (cycle: number) => To;
} {
  const matches = useMatches();
  const location = useLocation();
  const match = [...matches].reverse().find((m) => m.handle != null);
  const handle = (match?.handle ?? {}) as CycleHandle;
  const params = match?.params ?? {};
  return {
    cycle: handle.cycle?.(params),
    target: (cycle) => (handle.cycleTarget ?? defaultCycleTarget)(cycle, params, location),
  };
}
