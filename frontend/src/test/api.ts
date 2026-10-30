import { setupServer } from "msw/node";
import { createOpenApiHttp } from "openapi-msw";
import { apiBaseUrl } from "../config";
import type { paths } from "../api/schema";

/**
 * MSW handlers typed from the same OpenAPI document as the client: a path, parameter or
 * response body the API does not have is a type error.
 *
 *     server.use(http.get("/v1/meta", ({ response }) => response(200).json(meta)));
 */
export const http = createOpenApiHttp<paths>({ baseUrl: apiBaseUrl });

/** The mock API every test file runs against (`setup.ts`); a request no handler answers fails. */
export const server = setupServer();
