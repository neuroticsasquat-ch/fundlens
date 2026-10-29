/// <reference types="vite/client" />

/** The commit the bundle was built from, or "dev" outside Workers Builds (see vite.config.ts). */
declare const __BUILD_SHA__: string;

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
