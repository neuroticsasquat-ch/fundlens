import { render } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import type { HttpHandler } from "msw";
import type { ReactElement, ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import Providers from "../Providers";
import { routes } from "../routes";
import { http, server } from "./api";
import { CYCLES, META, problem, RACES, SEARCH_CALLOWAY } from "./fixtures";

/** The fixture API: the 2024 cycle, its races, and hits for any query containing "calloway". */
export const fixtureApi = (): HttpHandler[] => [
  http.get("/v1/cycles", ({ response }) => response(200).json(CYCLES)),
  http.get("/v1/meta", ({ response }) => response(200).json(META)),
  http.get("/v1/cycles/{cycle}/races", ({ params, response }) =>
    params.cycle === "2024"
      ? response(200).json(RACES)
      : response(404).json(problem(404, "Not Found", `No cycle ${params.cycle}.`)),
  ),
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
