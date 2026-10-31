---
status: accepted
---

# Mantine is the SPA's component library

The project spec (§8) first said "no component library beyond what closinglineup uses", and closinglineup uses none: hand-written CSS, light-only, desktop-first with a 1024 px minimum. fundlens.org is different in kind: a public site whose readers open race links from phones, that must follow the system's light or dark preference, and whose every page is tables, a search combobox and a few charts. Planning NEU-2043 (2026-10-30) decided the SPA adopts Mantine (`@mantine/core`, `@mantine/hooks`) for layout, tables, inputs, the search combobox, the drawer and the colour scheme, with ECharts kept as the only charting library and a thin set of our own components (`DataTable`, `QueryStatus`, `EChart`) over it. Spec §8 is amended accordingly.

Mantine over the alternatives because it ships every piece the shell needs in one themed package with a CSS-based styling system (no Tailwind, no runtime CSS-in-JS), `defaultColorScheme="auto"` for the system preference, a documented Vitest setup, and a `Combobox` that gives the typeahead its keyboard and ARIA behaviour for free.

## Considered options

- **Plain CSS, as closinglineup.** Rejected: every table, combobox, drawer, responsive grid and dark palette would be built and maintained by hand for a public audience; the shell ticket would spend its budget on primitives.
- **Headless primitives only (Radix, React Aria) with our CSS.** Rejected: correct behaviour for the combobox and menus, but two idioms in one small app and all the visual work still ours.
- **shadcn/ui + Tailwind.** Rejected: copy-in components mean we own and update them, and it brings Tailwind, cmdk and TanStack Table to match what Mantine has in the box.
- **MUI.** Rejected: Emotion runtime styling and a Material look that needs theming work not to read as a Google app.
- **Chakra UI v3.** Rejected: a smaller ecosystem than Mantine and recent breaking changes.

## Consequences

Mantine majors track React majors; upgrades land through Dependabot like every other dependency. The vitest setup carries Mantine's jsdom stubs (`matchMedia`, `ResizeObserver`, `scrollIntoView`). closinglineup remains the reference for the Vite/TS/oxlint/vitest toolchain and the ECharts wrapper, not for layout or styling.
