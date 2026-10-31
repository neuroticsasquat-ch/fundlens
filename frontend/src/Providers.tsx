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
  return (
    <MantineProvider theme={theme} defaultColorScheme="auto" env={env}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MantineProvider>
  );
}

export default Providers;
