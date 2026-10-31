import { screen } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { $api } from "../api/client";
import { http } from "../test/api";
import { renderWithProviders } from "../test/app";
import { problem } from "../test/fixtures";
import { server } from "../test/api";
import QueryStatus from "./QueryStatus";

function Meta({ notFound }: { notFound?: string }) {
  const query = $api.useQuery("get", "/v1/meta");
  return (
    <QueryStatus query={query} notFound={notFound}>
      {(meta) => <p>Build {meta.build_id}</p>}
    </QueryStatus>
  );
}

describe("QueryStatus", () => {
  it("shows a loading status, then the data", async () => {
    server.use(
      http.get("/v1/meta", ({ response }) =>
        response(200).json({
          build_id: "b1",
          published_at: "2024-11-03T08:00:00Z",
          resolver_version: null,
          model_version: null,
          precision: null,
          recall: null,
          cycles: {},
        }),
      ),
    );
    renderWithProviders(<Meta />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByText("Build b1")).toBeInTheDocument();
  });

  it("shows a problem's title and detail", async () => {
    server.use(
      http.get("/v1/meta", ({ response }) =>
        response.untyped(
          Response.json(problem(500, "Internal Server Error", "It broke."), { status: 500 }),
        ),
      ),
    );
    renderWithProviders(<Meta />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Internal Server Error");
    expect(alert).toHaveTextContent("It broke.");
  });

  it("says there is no published data on a 503", async () => {
    server.use(
      http.get("/v1/meta", ({ response }) =>
        response(503).json(problem(503, "Service Unavailable", "No gold build is live.")),
      ),
    );
    renderWithProviders(<Meta />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "fundlens has no published data yet. Try again after the next weekly build.",
    );
  });

  it("renders the page's not-found content for a 404, and the alert without one", async () => {
    server.use(
      http.get("/v1/meta", ({ response }) =>
        response.untyped(
          Response.json(problem(404, "Not Found", "No such thing."), { status: 404 }),
        ),
      ),
    );
    const { unmount } = renderWithProviders(<Meta notFound="Nothing by that name." />);
    expect(await screen.findByText("Nothing by that name.")).toBeInTheDocument();
    unmount();

    renderWithProviders(<Meta />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No such thing.");
  });

  it("says it could not reach the API when there is no problem body", async () => {
    function Failing() {
      const query = useQuery({
        queryKey: ["failing"],
        queryFn: () => Promise.reject(new TypeError("Failed to fetch")),
      });
      return <QueryStatus query={query}>{() => null}</QueryStatus>;
    }
    renderWithProviders(<Failing />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't reach the API.");
  });
});
