#!/bin/sh
# Generate src/api/schema.d.ts from the API's OpenAPI document, read on stdin (spec §7.2):
#
#   task fe:generate    # exports openapi.json from the backend, then runs this on it
#
# The types are committed, and CI regenerates them and fails if anything changed, so the SPA
# cannot drift from the API (ADR-0003). `src/api/client.ts` is the hand-written client over them.
set -eu

cd "$(dirname "$0")/.."

dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
cat > "$dir/openapi.json"

# `--root-types`: every schema as its own export too (`Race`, `Meta`), not only under
# `components["schemas"]`.
pnpm exec openapi-typescript "$dir/openapi.json" \
  --root-types --root-types-no-schema-prefix \
  --output src/api/schema.d.ts
