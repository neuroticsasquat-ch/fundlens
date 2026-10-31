import { QueryClient } from "@tanstack/react-query";
import type { Problem } from "./client";

/** Whether `error` is an API problem document, which every API error body is. */
export function isProblem(error: unknown): error is Problem {
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as Partial<Problem>).status === "number" &&
    typeof (error as Partial<Problem>).title === "string"
  );
}

/** The app's query cache. The data changes weekly, so a fetched page stays fresh for a while. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
        // A 4xx says the request is wrong, and asking again will not change that.
        retry: (failureCount, error) =>
          failureCount < 2 && !(isProblem(error) && error.status < 500),
      },
    },
  });
}
