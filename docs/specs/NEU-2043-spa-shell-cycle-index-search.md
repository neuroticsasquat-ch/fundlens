# NEU-2043 — SPA shell, layout, cycle index and search

**Ticket:** [NEU-2043](https://linear.app/neuroticsasquatch/issue/NEU-2043) · **Milestone:** M2 One cycle, committee-level · **Parent story:** NEU-2019
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §7.2, §8 (amended by this spec), §12 · **ADRs:** 0003 (SPA in `frontend/`, deployed as a Worker), 0008 (Mantine; written with this spec)
**Blocked by:** NEU-2042 (merged: generated client, MSW, build SHA). **Blocks:** NEU-2044, NEU-2045, NEU-2056, NEU-2066, which inherit the contracts in §9.

Planned 2026-10-30. `/implementit NEU-2043` implements straight from this file.

## 1. What and why

The placeholder SPA has one route and no way to find a race. This ticket builds the shell every page renders inside (header with cycle switcher and search, footer, theme), the shared components the page tickets reuse (data table, query status, chart wrapper, formats), and the three entry-point pages: home, the race index for a cycle, and search results. Every §8 route exists after this ticket; the ones whose pages are not built yet render an honest stub.

### 1.1 Decisions this spec pins (the ticket asked `/planit` to)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Component library | **Mantine 9** (`@mantine/core`, `@mantine/hooks`), ADR-0008. Project spec §8's "no component library beyond what closinglineup uses" is amended. | Plain CSS as closinglineup: every table, combobox, drawer and dark palette would be hand-built for a public, phone-facing site. Headless primitives only: two idioms for one app. |
| Viewport | Responsive, phone up. Mantine `AppShell`; under the `sm` breakpoint (48em) the cycle switcher and nav link move into a Burger-opened Drawer, tables scroll inside `Table.ScrollContainer`, grids collapse to one column. | Desktop-first like closinglineup: journalists open race links from phones. |
| Theme | Mantine defaults: system font stack, `primaryColor: "blue"`, `defaultRadius: "sm"`, `defaultColorScheme="auto"` (system preference, no toggle, spec §8). Party colours are tokens, never the primary. | A bespoke palette or webfont now: design debt before any page exists. |
| Table | Our `DataTable<T>` over Mantine `Table` with typed column definitions and a small client-side sort (§6.1). | `mantine-datatable` (a dependency tracking Mantine majors, its sort API shaping ours), `mantine-react-table` (a data grid no page needs). |
| Query layer | `openapi-react-query` over the shipped `openapi-fetch` client: `$api.useQuery("get", "/v1/cycles/{cycle}/races", { params })`, typed from `schema.d.ts`, keys derived from method, path and params. | Hand-written hooks per route (closinglineup): one more file to keep in step with the contract. |
| Charts | Port closinglineup's `EChart` wrapper and tree-shaken `echarts/core` registration, plus a theme bridge from Mantine's resolved colour scheme (§6.3). **No chart is drawn in this ticket**; the first is NEU-2044's. | A per-cycle totals bar on the home page: one bar until NEU-2059 merges cycles. |
| Header | Brand · cycle switcher · search (takes the remaining width) · "Races" link. Dataset and Methodology are footer links only. | Full nav in the header; or search alone. |
| Cycle switcher | Context-aware through a per-route `handle.cycleTarget` (§4.2); routes without one go to that cycle's index. No preflight request. | Always to the index: loses "this race, other cycle". Preflighting the race: a request per switch to avoid a 404 the race page already handles. |
| Search | Header typeahead (Mantine `Combobox`) **and** a `/search?q=` results page (§4.3, §5.3). | Typeahead only (no shareable results URL); submit-to-page only (no inline results). |
| Race index | Three office sections (President, Senate, House) as stacked headings with anchors, one sortable `DataTable` each, a client-side state filter (§5.2). | Tabs (a section would not be linkable); state sub-header rows; a state-first accordion. |
| Home | Tagline, large search, three stat tiles for the current cycle, three office cards, data-as-of line (§5.1). | Redirecting `/` to the index. |
| Footer | Links row, provenance row (build, published date, 104.15 notice, CC BY 4.0), build SHA row (§4.4). | Links and SHA only. |
| Page states | `ComingSoon` stubs for unbuilt routes, `NotFound` for unknown paths, a ported `QueryStatus` with a 503 message (§6.2). | Stubs rendering NotFound (footer links would dead-end). Per-page skeletons (work in every page ticket). |
| Formats | Full dollars in tables, compact in tiles and on axes, ISO dates, em dash for missing (§6.4). | Compact everywhere (loses exact figures); full everywhere (wide phone tiles). |
| Special races | The SPA mirrors the API: `/race/2024/senate/NE?special=1`. | A `-special` path suffix the API does not take. |
| Icons | None. No icon package in this ticket; Mantine's own `Burger`, `CloseButton` and `Loader` cover the shell. | `@tabler/icons-react` for one search glyph. |

### 1.2 Not in scope

Race, candidate, committee, donor, dataset and methodology pages (their routes render `ComingSoon`). Any chart. Server-side anything: the Worker stays assets-only. Analytics (spec §8: none in v1). A colour-scheme toggle. Donor search results have no page until M3 (`/donor/:id` is a stub); the ticket's `musk` example is an M3 donor, so this ticket's tests search the fixture's `calloway` (a candidate and a committee, two groups).

## 2. Dependencies and toolchain changes

Added with `docker compose exec frontend pnpm add …` (lockfile lands through the bind mount):

| Package | Why |
|---|---|
| `@mantine/core`, `@mantine/hooks` (9.x; peer React ^19.2) | The component library. Styles: `import "@mantine/core/styles.css"` once, in `main.tsx`, before `index.css`. |
| `openapi-react-query` (0.5.x; peer `openapi-fetch` ^0.17, `@tanstack/react-query` ^5.80) | The query layer. |
| dev: `postcss`, `postcss-preset-mantine`, `postcss-simple-vars` | Mantine's PostCSS preset; `frontend/postcss.config.cjs` exactly as the Mantine Vite guide gives it, with the five `mantine-breakpoint-*` variables. |

`index.html` keeps `<meta name="color-scheme" content="light dark">`; `index.css` keeps its `color-scheme: light dark` root and `light-dark()` page background so nothing flashes before Mantine mounts, and loses `.shell`/`.build` (the shell is Mantine's). Mantine's `ColorSchemeScript` is not needed: a client-only SPA renders nothing before the provider applies the system scheme.

`src/test/setup.ts` gains the stubs Mantine's Vitest guide lists (`matchMedia`, `ResizeObserver`, `scrollIntoView`, `getComputedStyle` wrapper, `document.fonts`), ahead of the MSW lifecycle it already has. `matchMedia`'s stub is a `vi.fn` the theme test re-implements per case (§7).

## 3. Layout

```
frontend/postcss.config.cjs
frontend/src/main.tsx                 styles import, StrictMode, <App/>
frontend/src/App.tsx                  MantineProvider(theme, defaultColorScheme="auto") › QueryClientProvider › RouterProvider
frontend/src/theme.ts                 createTheme({ primaryColor: "blue", defaultRadius: "sm" }); PARTY_COLOURS
frontend/src/routes.tsx               every §8 route under <Layout/>, each with its handle (§4.2)
frontend/src/api/client.ts            + export const $api = createClient(api)  (openapi-react-query)
frontend/src/api/query.ts             createQueryClient(): staleTime 5 min, no refetch on focus, retry rule (§6.2)
frontend/src/shell/Layout.tsx         AppShell: Header, Drawer, Footer, <Outlet/>
frontend/src/shell/Header.tsx         brand, CycleSwitcher, SearchBox, Races link, Burger
frontend/src/shell/CycleSwitcher.tsx
frontend/src/shell/cycleTarget.ts     CycleHandle type, defaultCycleTarget, useCycleTarget()
frontend/src/shell/Footer.tsx
frontend/src/search/SearchBox.tsx     the header combobox
frontend/src/search/target.ts         searchTarget(result): the route a hit opens; kind labels and order
frontend/src/pages/HomePage.tsx
frontend/src/pages/CyclePage.tsx      /cycles/:cycle
frontend/src/pages/SearchPage.tsx     /search
frontend/src/pages/ComingSoon.tsx     stub for unbuilt routes (takes the page's name)
frontend/src/pages/NotFound.tsx
frontend/src/components/DataTable.tsx
frontend/src/components/QueryStatus.tsx
frontend/src/components/StatTile.tsx
frontend/src/components/charts/echarts.ts   registration + ChartOption (ported)
frontend/src/components/charts/EChart.tsx   (ported)
frontend/src/components/charts/theme.ts     useChartTheme(): the Mantine → ECharts bridge
frontend/src/components/format.ts     money, moneyCompact, count, isoDate, DASH
frontend/src/components/usePageTitle.ts
frontend/src/domain/states.ts         STATE_NAMES, raceLabel(), officeLabel()
frontend/src/test/setup.ts            + Mantine stubs
frontend/src/test/app.tsx             renderApp(path): providers + memory router over `routes`
frontend/src/test/echarts.ts          (ported) the jsdom stand-in for charts/echarts
frontend/src/test/fixtures.ts         typed CYCLES, RACES (the five fixture races), SEARCH_CALLOWAY, META
```

Component files export one default component; helpers are named exports. No file imports `echarts` except `components/charts/echarts.ts`.

## 4. The shell

### 4.1 Layout and header

`AppShell` with `header={{ height: 56 }}`, `padding="md"`, content in `Container size="xl"`. The header row, left to right: brand link "fundlens" to `/`; `CycleSwitcher`; `SearchBox` (`flex: 1`); `Races` link to `/cycles/{current}`; a `Burger` visible below `sm` that opens a `Drawer` holding the switcher and the link. Above `sm` the Burger is hidden (`hiddenFrom`/`visibleFrom`; CSS, not state). The search box stays in the header at every width.

**Current cycle** (CONTEXT.md): the newest cycle in `/v1/cycles`. The header fetches `/v1/cycles` once (shared with every page through the query cache) and `/v1/meta` once for the footer.

### 4.2 Cycle switcher

A Mantine `Select` labelled "Cycle" (`aria-label`), options from `/v1/cycles` newest first, `allowDeselect={false}`, disabled while cycles load. Its value is the **route's cycle** when the matched route exposes one, else the current cycle. Choosing a cycle navigates to the target the deepest matched route declares:

```ts
// shell/cycleTarget.ts
export type CycleHandle = {
  /** The route's cycle, shown in the switcher; undefined when the URL has none. */
  cycle?: (params: Params) => number | undefined;
  /** Where picking `cycle` goes from this route. */
  cycleTarget?: (cycle: number, params: Params, location: Location) => To;
};
export const defaultCycleTarget = (cycle: number): To => `/cycles/${cycle}`;
```

`useCycleTarget()` reads `useMatches()`, takes the last match with a `handle`, and falls back to the default. The routes declare, **now, in `routes.tsx`, including the stubs**, so the shell's tests cover the table before the pages exist and the page tickets only replace the element:

| Route | `cycle` | `cycleTarget(c)` |
|---|---|---|
| `/` | none | `/cycles/{c}` |
| `/cycles/:cycle` | `:cycle` | `/cycles/{c}` |
| `/race/:cycle/:office/:place` | `:cycle` | `/race/{c}/{office}/{place}` (the `?special=1` query is dropped) |
| `/candidate/:id`, `/committee/:id` | none | `{ pathname: location.pathname, hash: "cycle-{c}" }`: the page scrolls to that cycle's row (NEU-2045 gives each cycle row `id="cycle-{c}"`) |
| `/donor/:id`, `/search`, `/dataset`, `/methodology`, `*` | none | `/cycles/{c}` |

When the target race does not exist in the chosen cycle, the race page's own not-found state (NEU-2044) says so and links to that cycle's index. The shell makes no preflight request.

### 4.3 Search box

Mantine `Combobox` around a `TextInput` (`aria-label="Search"`, placeholder "Search races, candidates, committees").

- The typed value is debounced 250 ms (`useDebouncedValue`). `/v1/search?q=` is queried when the debounced value has **2 or more characters** (the API's `min_length`); shorter shows no dropdown.
- The dropdown groups hits by kind with `Combobox.Group`, in the order **Races, Candidates, Committees, Donors**, omitting empty groups; within a group hits keep the API's order (score desc). Each option shows `name` (a race's is the API's label, `2024 Senate MD`) and, dimmed, `aliases` when present, except for races, whose alias is the slug and is not shown. A final option "All results for ‘{q}’" goes to `/search?q={q}`. While the query is pending the dropdown shows "Searching…"; with no hits, "No results for ‘{q}’" plus the all-results option.
- Keyboard: Down/Up move the active option; Enter opens the active option; **Enter with no active option opens the top hit**, which is the first result the API returned (the highest score across every kind, not the first of the first group); Escape closes the dropdown and keeps the text. Enter with fewer than 2 characters navigates to `/search?q=` anyway, where the page says what is needed.
- Opening a hit navigates and clears the box.

`searchTarget(result)` (unit tested) maps a hit to its route: `race` → `/race/{aliases}` where `aliases` is the race's slug (`gold.search_entity` puts the slug there), with a trailing `-special` stripped into `?special=1`; `candidate` → `/candidate/{id}`; `committee` → `/committee/{id}`; `donor` → `/donor/{id}`.

### 4.4 Footer

Three rows inside the container, small dimmed text:

1. Links: Dataset (`/dataset`) · Methodology (`/methodology`) · GitHub (`https://github.com/neuroticsasquat-ch/fundlens`) · API (`https://api.fundlens.org/docs`).
2. Provenance, rendered only once `/v1/meta` has data: "Source: FEC bulk data · build {build_id} published {isoDate(published_at)}". Then, always: "Contributor information may not be sold or used for commercial purposes or to solicit contributions (11 CFR 104.15)." and "Dataset: CC BY 4.0."
3. "fundlens · build {buildSha}" (`config.ts`, unchanged).

### 4.5 Theme

`MantineProvider` with `theme.ts` and `defaultColorScheme="auto"`. No toggle. `theme.ts` also exports `PARTY_COLOURS`: `DEM` → `blue.6`, `REP` → `red.6`, anything else → `gray.6`, read through `useMantineTheme()` so they resolve in both schemes; used only where party is the meaning (NEU-2044's chart and badges).

## 5. Pages

Every page calls `usePageTitle(title)`; `document.title` is `"{title} · fundlens"`, the home page's is `"fundlens"`.

### 5.1 Home (`/`)

Queries: `/v1/cycles`, `/v1/meta` (both cached from the shell). Content, top to bottom:

- Tagline (`Title order={1}`): "Who funds federal races." and a one-sentence subtitle: "Donor, candidate and committee money for every federal race since 1980, with donors resolved across name, employer and address variants."
- A large `SearchBox` (the same component, `size="lg"`, autofocused on this page only).
- Three `StatTile`s in a `SimpleGrid cols={{ base: 1, sm: 3 }}` for the current cycle: "Races" `count(race_count)`, "Contributions counted" `count(contribution_count)`, "Raised" `moneyCompact(total_amount)` with the full figure as `title`. Each tile links to `/cycles/{current}`. A caption above them: "{current} cycle · data as of {isoDate(meta.published_at)}" (the date omitted while meta is unavailable).
- Three cards President / Senate / House linking to `/cycles/{current}#president|senate|house`.
- When `/v1/cycles` has more than one cycle, a "Earlier cycles" line listing the others as links to their index.

### 5.2 Cycle index (`/cycles/:cycle`)

Queries: `/v1/cycles/{cycle}/races` (one request, no `office`/`state` filter; the filter is client-side) and `/v1/cycles` (cached). A non-integer `:cycle` renders `NotFound`; the API's 404 (a cycle gold does not have) renders `QueryStatus`'s `notFound`: "No {cycle} cycle" with a link home.

- `Title`: "{cycle} races"; subtitle from the cycle row: "{count(race_count)} races · {moneyCompact(total_amount)} raised".
- A `Select` "State" (`aria-label`) with "All states" and the states present in the response (by name, sorted), filtering every section client-side. President (`state = US`) is never filtered out.
- Three sections, each a `Title order={2}` with `id` `president`, `senate`, `house` and a `DataTable`:
  - Columns: **Race** (link to `/race/{slug}` via the same slug→route rule as `searchTarget`), **Candidates** (`count(candidate_count)`), **From individuals** (`money(total_individual)`), **From committees** (`money(total_committee)`), **Total** (`money(total_individual + total_committee)`). Numbers right-aligned; `Total` and the money columns sortable; default sort is the API's order (state, then district, specials after the regular race).
  - Race labels (`domain/states.ts`): President → "President"; Senate → the state name, plus " special" when `is_special` ("Nebraska special"); House → "{State} {ordinal}" ("Maryland 5th"), district `00` → "{State} at-large". `STATE_NAMES` covers the 50 states, DC, the delegate territories PR, GU, VI, AS, MP, and `US` → "United States". An unknown code falls back to the code.
  - A race with `candidate_count = 0` renders its row dimmed (`c="dimmed"`), still linked.
  - A section with nothing after the filter shows "No {office} races in {state}." instead of an empty table; a section absent from the response altogether (a cycle without a presidential race) is omitted.

The fixture cycle renders President · United States; Senate · Maryland and Nebraska special (dimmed); House · Maryland 5th and Maryland 8th (dimmed).

### 5.3 Search results (`/search?q=`)

Reads `q` from the URL. Fewer than 2 characters: "Type at least two characters to search." No query is sent. Otherwise `/v1/search?q=` and, grouped by kind in the §4.3 order with a `Title order={2}` each, a list of hits: the name as a link (`searchTarget`), `aliases` dimmed (not for races), and a kind `Badge`. No hits: "No results for ‘{q}’." Title: "Search: {q}".

### 5.4 Stubs

`ComingSoon` takes `name` ("Race", "Candidate", "Committee", "Donor", "Dataset", "Methodology") and renders "{name} pages are coming." with a link home; the route table in §4.2 lists which paths render it. `NotFound` (`path: "*"`) renders "There is no page at {pathname}." with a link home. Both set their titles.

## 6. Shared components

### 6.1 `DataTable<T>`

```ts
type Column<T> = {
  key: string;
  header: string;
  align?: "left" | "right";          // right also sets tabular-nums
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => number | string | null;   // present ⇒ sortable
};
type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  caption?: string;
  defaultSort?: { key: string; direction: "asc" | "desc" };   // unset ⇒ the rows' own order
  rowProps?: (row: T) => Partial<ComponentProps<typeof Table.Tr>>;   // dimming, ids
  emptyMessage?: string;             // rendered instead of the table when rows is empty
};
```

Mantine `Table` (`striped`, `highlightOnHover`) inside `Table.ScrollContainer minWidth={640}`. A sortable column's header is a `UnstyledButton`; clicking sorts descending first for numbers and ascending first for strings, a second click flips, and the `th` carries `aria-sort`. `null` sort values go last in either direction. Sorting is a stable client-side sort over `rows`; the component holds the sort state.

### 6.2 `QueryStatus<T>` and the query client

```ts
function QueryStatus<T>({ query, children, notFound }: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  notFound?: ReactNode;              // rendered for a 404 problem instead of the alert
})
```

Pending: a centred `Loader` in an element with `role="status"` and `aria-label="Loading"`. Error: a `Problem` (every API error body is one) renders an `Alert role="alert" color="red"` titled with the problem's `title` and showing its `detail`; a 503 shows "fundlens has no published data yet. Try again after the next weekly build."; a 404 renders `notFound` when given. A network failure (no problem body) shows "Couldn't reach the API."

`createQueryClient()`: `staleTime` 5 minutes, `refetchOnWindowFocus: false`, and retry only below 2 attempts **and** only when the error is not a problem with `status < 500`. `openapi-react-query`'s query function throws the client's `error` object (the problem), so `query.error` is the typed `Problem`.

### 6.3 `EChart` and `useChartTheme`

`components/charts/echarts.ts` and `EChart.tsx` are closinglineup's, with the registration trimmed to `BarChart`, `LineChart`, `GridComponent`, `TooltipComponent`, `LegendComponent`, `CanvasRenderer` (a page ticket adds a series or component when it draws one). `src/test/echarts.ts` is the ported stand-in; a chart test mocks `./echarts` with it and reads `lastOption()`.

`useChartTheme()` returns `{ ink, dimmed, axis, grid, background: "transparent", party: PARTY_COLOURS }` from `useComputedColorScheme("light")` and `useMantineTheme()`: light → `theme.black`, `gray.6`, `gray.5`, `gray.2`; dark → `dark.0`, `dark.2`, `dark.3`, `dark.5`. `EChart` takes `option` and spreads `textStyle: { color: ink }` and `backgroundColor` over it so every chart follows the scheme without each page repeating it. No chart is rendered in this ticket; the hook and the wrapper are tested directly.

### 6.4 `format.ts`

| Function | Output |
|---|---|
| `money(v)` | `$1,234,567`; negatives `−$1,200` (U+2212); `null` → `—` |
| `moneyCompact(v)` | `$1.2M`, `$54.8K`, `$975` (Intl `notation: "compact"`, one decimal above 1,000) |
| `count(v)` | `1,234` |
| `isoDate(v)` | the date part of an ISO timestamp or date string: `2024-11-03` |
| `DASH` | `—` |

Right-aligned numeric cells use `font-variant-numeric: tabular-nums`.

## 7. Tests (vitest, jsdom, MSW typed handlers; `task fe:test`, `task fe:lint`, `task fe:typecheck`)

`renderApp(path)` renders `routes` in a memory router under `MantineProvider` (with `env="test"`) and a fresh query client with `retry: false`, and returns the router for location assertions. Fixtures in `src/test/fixtures.ts` are typed from the client (`Cycle`, `RaceSummary`, `SearchResult`, `Meta`) and mirror `tests/fixtures/fec/2024/expected.yaml`: the five races with their totals, one cycle row, and `calloway` search results (candidate `H4MD05106` "CALLOWAY, RUTH" with alias "CALLOWAY FOR CONGRESS", committee `C00800106`, committee `C00800114` "CALLOWAY LEADERSHIP FUND").

| File | Covers |
|---|---|
| `shell/Layout.test.tsx` | Header links; the switcher shows the current cycle on `/`, the route's on `/cycles/2022` and `/race/2022/senate/MD`; picking a cycle lands on the §4.2 target for every row of the table (including the stub routes and the hash form); the Burger opens the Drawer holding the switcher; the footer shows the four links, the provenance line once meta loads and not before, the 104.15 notice, and `build dev`. |
| `search/SearchBox.test.tsx` | Fake timers: no request under 2 characters, one request after the debounce; grouping and order; Enter with no highlight goes to the API's first hit; Down+Enter goes to that option; the all-results option; Escape; "No results". |
| `search/target.test.ts` | Each kind's route; the `-special` slug. |
| `pages/HomePage.test.tsx` | Tagline, three tiles with the fixture figures (`$2.2M`), tile links, office card anchors, data-as-of line, earlier-cycles line only with two cycles, title. |
| `pages/CyclePage.test.tsx` | The five fixture races in the right sections with the right labels and links; dimmed empty races; the state filter leaving President; sorting by Total via the header button and `aria-sort`; 404 → not-found text; non-integer cycle → NotFound; title. |
| `pages/SearchPage.test.tsx` | Under-two-characters message without a request; grouped results with badges and links; no results. |
| `routes.test.tsx` | Every §8 path renders its page or its `ComingSoon` with the right name; an unknown path renders NotFound; footer links reach the stubs. |
| `components/DataTable.test.tsx` | Default order, numeric desc-first then flip, string asc-first, nulls last, `aria-sort`, `emptyMessage`, `rowProps`. |
| `components/QueryStatus.test.tsx` | Pending role, problem alert, 503 text, 404 `notFound`, network failure text. |
| `components/charts/theme.test.tsx`, `EChart.test.tsx` | With `matchMedia` answering `prefers-color-scheme: dark` the hook's `ink` is the dark value and `EChart` sets it on the option; light otherwise. The ported `EChart` tests (mount, `notMerge`, click, dispose). |
| `components/format.test.ts`, `domain/states.test.ts`, `usePageTitle.test.tsx` | The §6.4 table; labels for the five fixture races plus an at-large and a territory; title suffix. |

Responsive behaviour is CSS (`hiddenFrom`/`visibleFrom`, grid `cols` by breakpoint) and is checked by eye in `task fe:dev` at 375 px and 1280 px, not in jsdom, which has no layout. The Vite proxy, the Worker and CI are unchanged; CI's `tsc -b`, oxlint and vitest must pass with the new packages.

## 8. Acceptance criteria (the ticket's DoD, as amended by this spec)

- [ ] `/cycles/2024` on the fixture-backed API (`task db:seed`) lists every fixture race in its office section with the §5.2 labels, the empty races dimmed, and each race links to its `/race/…` route (a `ComingSoon` page until NEU-2044).
- [ ] Typing `calloway` in the header search shows a Candidates group and a Committees group; Enter with nothing highlighted navigates to the top hit; `/search?q=calloway` lists the same hits grouped. (`musk` behaves the same once M3 adds donor rows.)
- [ ] The shell renders the build SHA from Workers Builds (`dev` elsewhere), the footer provenance from `/v1/meta`, and the theme follows the system preference: the OS set to dark renders Mantine's dark scheme and the chart theme's dark ink (tested through `matchMedia`).
- [ ] The cycle switcher follows the §4.2 table on every route (tested).
- [ ] `task fe:test`, `task fe:lint`, `task fe:typecheck` and `task fe:build` pass; `pnpm build` output still deploys as an assets-only Worker.

## 9. Contracts for the following page tickets

- **NEU-2044 (race page):** replace the `/race/:cycle/:office/:place` element; keep the route's `handle`; read `?special`. Render inside `QueryStatus` with `notFound` = "No {office} race for {place} in {cycle}" linking to `/cycles/{cycle}`. Use `DataTable` for candidates and top committees, `EChart` + `useChartTheme` + `PARTY_COLOURS` for the split, `money`/`moneyCompact` from `format.ts`, `raceLabel` for the heading.
- **NEU-2045 (candidate, committee):** replace the elements, keep the handles, give every per-cycle row `id="cycle-{cycle}"` and scroll to `location.hash` on load and change. Share the contributions table through `DataTable` (cursor "load more" is page state).
- **NEU-2056, NEU-2066:** replace `/methodology` and `/dataset` stubs; the footer links already point at them.
- Every page: `usePageTitle`, `QueryStatus`, `$api.useQuery`; no page imports `echarts` or defines its own money format.

## 10. Open items left to later tickets

A per-cycle totals chart on the home page once NEU-2059 serves several cycles. Donor results and `/donor/:id` (M3). Whether `/search` wants `?kind=` filter chips (not asked for; the API supports it). Mantine's `Spotlight` as a ⌘K palette (nice, not asked for).
