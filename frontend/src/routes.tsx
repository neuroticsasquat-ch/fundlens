import type { RouteObject } from "react-router";
import HomePage from "./pages/HomePage";

// The real pages (spec §8) arrive with their tickets; this is the placeholder the Worker serves.
export const routes: RouteObject[] = [{ path: "/", element: <HomePage /> }];
