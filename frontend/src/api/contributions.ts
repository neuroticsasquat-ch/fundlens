import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import type { ContributionPage } from "./client";

/**
 * The paging options every `/contributions` query takes: the first page has no cursor
 * (openapi-fetch leaves a null parameter out), and each page's `next_cursor` fetches the next
 * until it is null.
 *
 *     $api.useInfiniteQuery("get", "/v1/committees/{committee_id}/contributions", init,
 *       CONTRIBUTION_PAGES)
 */
export const CONTRIBUTION_PAGES = {
  initialPageParam: null,
  getNextPageParam: (page: ContributionPage) => page.next_cursor,
};

/** A `/contributions` query's pages so far. */
export type ContributionsQuery = UseInfiniteQueryResult<InfiniteData<ContributionPage>, unknown>;
