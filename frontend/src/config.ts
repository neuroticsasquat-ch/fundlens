/** Origin of the public API; empty means same-origin, which the dev server proxies (`/v1`). */
export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

/** Short form of the commit the bundle was built from. */
export const buildSha = __BUILD_SHA__.slice(0, 7);
