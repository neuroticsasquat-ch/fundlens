import { render } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import type { HttpHandler } from "msw";
import type { ReactElement, ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import Providers from "../Providers";
import { routes } from "../routes";
import { http, server } from "./api";
import {
  CANDIDATE_OKAFOR,
  COMMITTEES,
  CONTRIBUTIONS,
  CYCLES,
  DONOR_IDS,
  DONOR_MARLOWE,
  MARLOWE_CONTRIBUTIONS,
  META,
  problem,
  RACE_PAGES,
  RACES,
  SEARCH_CALLOWAY,
} from "./fixtures";

/**
 * The fixture API: the 2024 cycle, its races and their pages, OKAFOR's candidate page, three
 * committees' pages, their 2024 contributions on one page, MARLOWE's donor page and his
 * contributions on one page (the id a merge retired redirecting to his), and hits for any query
 * containing "calloway".
 */
export const fixtureApi = (): HttpHandler[] => [
  http.get("/v1/cycles", ({ response }) => response(200).json(CYCLES)),
  http.get("/v1/meta", ({ response }) => response(200).json(META)),
  http.get("/v1/cycles/{cycle}/races", ({ params, response }) =>
    params.cycle === "2024"
      ? response(200).json(RACES)
      : response(404).json(problem(404, "Not Found", `No cycle ${params.cycle}.`)),
  ),
  http.get("/v1/races/{cycle}/{office}/{place}", ({ params, request, response }) => {
    const special = new URL(request.url).searchParams.get("special") === "true";
    const slug = `${params.cycle}/${params.office}/${params.place}${special ? "-special" : ""}`;
    const race = RACE_PAGES[slug];
    return race
      ? response(200).json(race)
      : response(404).json(problem(404, "Not Found", `No race ${slug}.`));
  }),
  http.get("/v1/candidates/{candidate_id}", ({ params, response }) =>
    params.candidate_id === CANDIDATE_OKAFOR.candidate_id
      ? response(200).json(CANDIDATE_OKAFOR)
      : response(404).json(problem(404, "Not Found", `No candidate ${params.candidate_id}.`)),
  ),
  http.get("/v1/candidates/{candidate_id}/contributions", ({ params, response }) =>
    response(200).json({
      contributions: CONTRIBUTIONS.filter((row) => row.candidate_id === params.candidate_id),
      next_cursor: null,
    }),
  ),
  http.get("/v1/committees/{committee_id}", ({ params, response }) => {
    const committee = COMMITTEES.find((c) => c.committee_id === params.committee_id);
    return committee
      ? response(200).json(committee)
      : response(404).json(problem(404, "Not Found", `No committee ${params.committee_id}.`));
  }),
  http.get("/v1/committees/{committee_id}/contributions", ({ params, response }) =>
    response(200).json({
      contributions: CONTRIBUTIONS.filter(
        (row) => row.recipient_committee_id === params.committee_id,
      ),
      next_cursor: null,
    }),
  ),
  http.get("/v1/donors/{donor_id}", ({ params, response }) => {
    if (params.donor_id === String(DONOR_IDS.mergedIntoMarlowe))
      return response(301).empty({ headers: { Location: `/v1/donors/${DONOR_IDS.marlowe}` } });
    return params.donor_id === String(DONOR_IDS.marlowe)
      ? response(200).json(DONOR_MARLOWE)
      : response(404).json(problem(404, "Not Found", `No donor ${params.donor_id}.`));
  }),
  http.get("/v1/donors/{donor_id}/contributions", ({ params, request, response }) => {
    const cycle = new URL(request.url).searchParams.get("cycle");
    return response(200).json({
      contributions: MARLOWE_CONTRIBUTIONS.filter(
        (row) =>
          String(row.donor_id) === params.donor_id && (!cycle || String(row.cycle) === cycle),
      ),
      next_cursor: null,
    });
  }),
  http.get("/v1/search", ({ request, response }) => {
    const q = new URL(request.url).searchParams.get("q") ?? "";
    return response(200).json(q.toLowerCase().includes("calloway") ? SEARCH_CALLOWAY : []);
  }),
];

const testQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });

/**
 * Renders the app at `path` against the fixture API, with `handlers` answering first, and
 * returns the router so a test can assert where it went.
 */
export function renderApp(path: string, { handlers = [] }: { handlers?: HttpHandler[] } = {}) {
  server.use(...handlers, ...fixtureApi());
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const result = render(
    <Providers queryClient={testQueryClient()} env="test">
      <RouterProvider router={router} />
    </Providers>,
  );
  return { router, ...result };
}

/** Renders a component under the app's providers, for one tested outside any page. */
export function renderWithProviders(ui: ReactElement): RenderResult {
  const queryClient = testQueryClient();
  // A wrapper, not part of `ui`, so `rerender` keeps the providers.
  const wrapper = ({ children }: { children: ReactNode }) => (
    <Providers queryClient={queryClient} env="test">
      {children}
    </Providers>
  );
  return render(ui, { wrapper });
}
