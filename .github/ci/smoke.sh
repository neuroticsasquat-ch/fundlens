#!/usr/bin/env bash
# Run by the shared image-check.yml on the prod image it built; $1 is its tag. The CLI starts,
# and the image's non-root user can write DATA_DIR and each cache directory under it, which a
# fresh volume inherits (docs/runbooks/coolify-setup.md).
set -euo pipefail

docker run --rm "$1" fundlens --version
docker run --rm --entrypoint sh "$1" -c '
  set -eu
  for d in /data/fundlens /data/fundlens/bronze /data/fundlens/silver /data/fundlens/scratch \
      /data/fundlens/resolution "$HOME"; do
    touch "$d/.smoke" && rm "$d/.smoke"
  done
  echo "writable as $(id -un)"
'
# What `fundlens dataset --snapshot` refuses to publish without (DATASET_DOCS_DIR, spec §9).
docker run --rm --entrypoint sh "$1" -c '
  set -eu
  for f in README.md LICENSE CHANGELOG.md schema/contribution.json; do
    test -s "/app/docs/dataset/$f"
  done
  echo "dataset docs present"
'
