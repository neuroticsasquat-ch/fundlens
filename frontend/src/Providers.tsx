import { MantineProvider } from "@mantine/core";
import type { QueryClient } from "@tanstack/react-query";
import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { theme } from "./theme";

/** Theme, colour scheme (the system's; no toggle) and query cache: what every page is inside. */
function Providers({
  queryClient,
  env,
  children,
}: {
  queryClient: QueryClient;
  env?: "default" | "test";
  children: ReactNode;
}) {
  // In tests, no global classes: they are what make `hiddenFrom`/`visibleFrom` hide anything, and
  // jsdom (from 31) applies their media queries at its fixed 1024px window, which would hide the
  // mobile-only Burger and Drawer with no way to test them at a narrow width.
  return (
    <MantineProvider
      theme={theme}
      defaultColorScheme="auto"
      env={env}
      withGlobalClasses={env !== "test"}
    >
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MantineProvider>
  );
}

export default Providers;
