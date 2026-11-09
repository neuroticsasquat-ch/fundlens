#!/usr/bin/env bash
# Run by the shared python.yml from the repo root after `uv sync` and before the checks.
#
# MinIO stands in for R2 as in docker-compose.yml. It runs here, not as an Actions service,
# because a service can't be given MinIO's `server /data` command. Then the two buckets
# `task buckets` creates, and the paths settings.py defaults to the image's /app and /data,
# which don't exist on the runner.
set -euo pipefail

docker run -d --name minio -p 9000:9000 \
  -e MINIO_ROOT_USER=fundlens -e MINIO_ROOT_PASSWORD=fundlens-dev-secret \
  cgr.dev/chainguard/minio:latest server /data

for _ in $(seq 60); do
  if curl -fs -o /dev/null http://localhost:9000/minio/health/live; then
    break
  fi
  sleep 1
done
curl -fsS -o /dev/null http://localhost:9000/minio/health/live

docker exec -e MC_HOST_local=http://fundlens:fundlens-dev-secret@localhost:9000 minio \
  mc mb --ignore-existing local/fundlens-data local/fundlens-public

# Absolute, so a test that changes directory still finds them. Through $GITHUB_ENV because
# .github/ci/env is literal and can't name the checkout.
{
  echo "SQL_DIR=$PWD/sql"
  echo "OVERRIDES_PATH=$PWD/resolution/overrides.yaml"
  echo "ADJUDICATE_PROMPT_PATH=$PWD/resolution/prompts/adjudicate_v1.md"
  echo "DATA_DIR=${RUNNER_TEMP:-/tmp}/fundlens-data"
} >> "$GITHUB_ENV"
