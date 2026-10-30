import { describe, expect, it } from "vitest";
import { http, server } from "../test/api";
import { api, type Meta } from "./client";

const meta: Meta = {
  build_id: "20241103T060000Z",
  published_at: "2024-11-03T08:00:00Z",
  resolver_version: null,
  model_version: null,
  precision: null,
  recall: null,
  cycles: { "2024": { build_id: "20241103T060000Z", source_dates: { indiv: "2024-11-02" } } },
};

describe("api client", () => {
  it("returns a route's typed body from the mock API", async () => {
    server.use(http.get("/v1/meta", ({ response }) => response(200).json(meta)));

    const { data, error } = await api.GET("/v1/meta");

    expect(error).toBeUndefined();
    expect(data).toEqual(meta);
  });

  it("sends the path parameters and returns a problem document as the error", async () => {
    server.use(
      http.get("/v1/candidates/{candidate_id}", ({ params, response }) =>
        response(404).json({
          type: "about:blank",
          title: "Not Found",
          status: 404,
          detail: `No candidate ${params.candidate_id}.`,
        }),
      ),
    );

    const { data, error } = await api.GET("/v1/candidates/{candidate_id}", {
      params: { path: { candidate_id: "S0MD00000" } },
    });

    expect(data).toBeUndefined();
    expect(error).toMatchObject({ status: 404, detail: "No candidate S0MD00000." });
  });
});
