/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Where the dev server forwards `/v1`. In compose the API is the `app` service; FastAPI's own
// default port otherwise. Production has no proxy: the bundle calls `VITE_API_BASE_URL` directly.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

// Workers Builds sets WORKERS_CI_COMMIT_SHA for every build; anywhere else the bundle says "dev".
const buildSha = process.env.WORKERS_CI_COMMIT_SHA ?? "dev";

export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD_SHA__: JSON.stringify(buildSha),
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/v1": { target: apiTarget, changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.test.{ts,tsx}"],
    // An absolute origin for the client and the MSW handlers (src/test/api.ts) to share: Node's
    // fetch, unlike a browser's, cannot resolve the same-origin `/v1/...` the default gives.
    env: { VITE_API_BASE_URL: "http://api.test" },
  },
});
