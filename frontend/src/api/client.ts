import createClient from "openapi-fetch";
import createQueryHooks from "openapi-react-query";
import { apiBaseUrl } from "../config";
import type { paths } from "./schema";

// Every response schema, by name (`Race`, `Meta`), for the pages that render them.
export type * from "./schema";

/**
 * The API, typed from its OpenAPI document: `api.GET("/v1/races/{cycle}/{office}/{place}", …)`
 * checks the path, its parameters and the response against `schema.d.ts`, which
 * `task fe:generate` writes and CI keeps in step with the backend.
 */
export const api = createClient<paths>({
  baseUrl: apiBaseUrl,
  // Looked up on each call rather than captured here, so a test's MSW server, which replaces
  // `globalThis.fetch` after this module has loaded, sees every request.
  fetch: (request) => globalThis.fetch(request),
});

/**
 * TanStack Query hooks over `api`, typed the same way and keyed by method, path and parameters:
 * `$api.useQuery("get", "/v1/cycles/{cycle}/races", { params: { path: { cycle } } })`. A failed
 * request's `error` is the API's problem document.
 */
export const $api = createQueryHooks(api);
