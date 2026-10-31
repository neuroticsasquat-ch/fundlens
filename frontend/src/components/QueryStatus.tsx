import { Alert, Center, Loader } from "@mantine/core";
import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { isProblem } from "../api/query";

/**
 * A page's loading and error states; `children` renders its data once it has arrived. A 404
 * renders `notFound` when the page gives one, so the page can say what was not there.
 */
function QueryStatus<T>({
  query,
  children,
  notFound,
}: {
  query: UseQueryResult<T, unknown>;
  children: (data: T) => ReactNode;
  notFound?: ReactNode;
}) {
  if (query.isPending) {
    return (
      <Center py="xl" role="status" aria-label="Loading">
        <Loader />
      </Center>
    );
  }
  if (query.isError) {
    const { error } = query;
    if (!isProblem(error)) {
      return (
        <Alert role="alert" color="red" title="Couldn't reach the API.">
          Check your connection and try again.
        </Alert>
      );
    }
    if (error.status === 404 && notFound !== undefined) return notFound;
    return (
      <Alert role="alert" color="red" title={error.title}>
        {error.status === 503
          ? "fundlens has no published data yet. Try again after the next weekly build."
          : error.detail}
      </Alert>
    );
  }
  return children(query.data);
}

export default QueryStatus;
