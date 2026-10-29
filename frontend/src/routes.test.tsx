import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { routes } from "./routes";

describe("routes", () => {
  it("renders the placeholder with the build SHA at /", () => {
    const router = createMemoryRouter(routes, { initialEntries: ["/"] });
    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "fundlens" })).toBeInTheDocument();
    // Outside Workers Builds the build is "dev".
    expect(screen.getByText("dev")).toBeInTheDocument();
  });
});
