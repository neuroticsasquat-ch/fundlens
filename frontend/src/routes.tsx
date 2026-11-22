import type { RouteObject } from "react-router";
import CandidatePage from "./pages/CandidatePage";
import CommitteePage from "./pages/CommitteePage";
import CyclePage from "./pages/CyclePage";
import DatasetPage from "./pages/DatasetPage";
import DonorPage from "./pages/DonorPage";
import HomePage from "./pages/HomePage";
import MethodologyPage from "./pages/MethodologyPage";
import NotFound from "./pages/NotFound";
import PayeePage from "./pages/PayeePage";
import RacePage from "./pages/RacePage";
import SearchPage from "./pages/SearchPage";
import Layout from "./shell/Layout";
import type { CycleHandle } from "./shell/cycleTarget";
import { defaultCycleTarget, parseCycle } from "./shell/cycleTarget";

// Every route of spec §8. A page ticket replaces its route's element and keeps its handle, which
// is what the cycle switcher reads (spec NEU-2043 §4.2).

const routeCycle: CycleHandle["cycle"] = (params) => parseCycle(params.cycle);

// A candidate's, committee's or payee's page lists every cycle; switching scrolls to its row.
const cycleRow: CycleHandle = {
  cycleTarget: (cycle, _params, location) => ({
    pathname: location.pathname,
    hash: `cycle-${cycle}`,
  }),
};

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      {
        path: "/cycles/:cycle",
        element: <CyclePage />,
        handle: { cycle: routeCycle, cycleTarget: defaultCycleTarget } satisfies CycleHandle,
      },
      {
        // `?special=1` is the special race; switching cycle goes to the regular one.
        path: "/race/:cycle/:office/:place",
        element: <RacePage />,
        handle: {
          cycle: routeCycle,
          cycleTarget: (cycle, params) => `/race/${cycle}/${params.office}/${params.place}`,
        } satisfies CycleHandle,
      },
      { path: "/candidate/:id", element: <CandidatePage />, handle: cycleRow },
      { path: "/committee/:id", element: <CommitteePage />, handle: cycleRow },
      { path: "/donor/:id", element: <DonorPage /> },
      { path: "/payee/:payeeId", element: <PayeePage />, handle: cycleRow },
      { path: "/search", element: <SearchPage /> },
      { path: "/dataset", element: <DatasetPage /> },
      { path: "/methodology", element: <MethodologyPage /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];
