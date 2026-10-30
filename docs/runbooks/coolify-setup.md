# Runbook: Coolify project setup

How to stand up fundlens's production services on Coolify (NEU-2032; spec §3.2, §10.1, §10.3, §10.4):
the `api`, the idle `pipeline` and `fundlens-postgres` from `docker-compose.prod.yml`, their environment,
Bugsink crash reporting, the two Uptime Kuma push monitors and the nightly Postgres backup. Run it once,
top to bottom. Append to the [Log](#log) at the bottom; never rewrite it.

**Not in this runbook:** the scheduled task (NEU-2063), Cloudflare DNS, R2 and tokens (NEU-2033), the
first data run (NEU-2046).

## Before you start

- **NEU-2033 is done up to its DNS, R2 and token steps.** This runbook needs, from its as-built section:
  the R2 endpoint, the R2 read/write token's access key ID and secret, the zone ID, the purge-only API
  token, and the proxied `api` record pointing at the Coolify host.
- You can sign in to Coolify, Bugsink (`https://bugsink.neuroticsasquat.ch`), Kuma
  (`https://kuma.tail1afe5a.ts.net`, tailnet only) and DeepInfra as the admin, and the laptop is on the
  tailnet.
- `ssh hetzner-01` works and `sudo -n true` succeeds there (ops `docs/runbooks/vm-ssh.md`).

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`, `138.201.223.253`): 8 cores, 62 GB |
| Coolify project / environment | `fundlens` / `production` |
| Resource | Git-based Docker Compose application, `neuroticsasquat-ch/fundlens` `main`, `/docker-compose.prod.yml` |
| Services | `api` (uvicorn on 8000, healthcheck `fundlens health`), `pipeline` (`sleep infinity`, 40 GB limit), `fundlens-postgres` (`postgres:18`) |
| Domain | `https://api.fundlens.org` → `api:8000` |
| Bugsink project | `fundlens` in team `neuroticsasquat.ch` |
| Kuma push monitors | `fundlens/weekly`, `fundlens/publish` |
| Container names | `<service>-<resource uuid>`, followed by `-<deploy timestamp>` on compose apps (new on every deploy), so match them by prefix |

**Why the database service is `fundlens-postgres`, not `postgres`.** "Connect to Predefined Network" puts
every service on Coolify's shared `coolify` network as well as the app's own, under its service name. A
bare `postgres` there can resolve to another stack's database. `DATABASE_URL` is built in the compose
file from `POSTGRES_PASSWORD` and that unique name.

**Why the check is `OTEL_RESOURCE_ATTRIBUTES`, not `SOURCE_COMMIT`.** On the other compose apps the
container's own `SOURCE_COMMIT` reads `unknown` even with *Source commit availability* on, while the
compose-interpolated values carry the real SHA (ops `docs/runbooks/backend-telemetry-env.md`, log
2026-10-18). fundlens reads only `OTEL_RESOURCE_ATTRIBUTES`, so that is what step 8 checks.

## 1. Create the project and the resource

1. Coolify → *Projects* → *+ Add*. Name `fundlens`. *Continue*. The `production` environment is created
   with it.
2. In `production`, *+ New* → *Private Repository (with GitHub App)*, using the GitHub App source the
   other NS apps deploy through. Pick repository `neuroticsasquat-ch/fundlens`, branch `main`.
3. *Build Pack* = **Docker Compose**. *Base Directory* = `/`. *Docker Compose Location* =
   `/docker-compose.prod.yml`. *Continue*. Do **not** deploy yet.
4. Copy the resource UUID from the browser's address bar (`…/application/<uuid>`). It names every
   container. Record it in the [Log](#log).

**Check:** the resource's *General* page lists three services: `api`, `pipeline`, `fundlens-postgres`.

## 2. Advanced settings

1. *Advanced* → *Build* → **Source commit availability** = **Available during build**. *Save*. Under the
   default (*Runtime only*) the compose interpolates `${SOURCE_COMMIT:-unknown}` as `unknown`.
2. *Advanced* → *Deployment* → tick **Connect to Predefined Network**. *Save*. SigNoz's collector,
   `otel-collector-b144lcfm2xe4mxo73dg7b8z9`, resolves only on the `coolify` network.

**Check:** reload the page; both settings are still set. (They have reverted after Coolify upgrades
before, so step 10 re-checks them.)

## 3. Domain

1. *General* → *Domains for api* = `https://api.fundlens.org:8000`. The `:8000` is the container port
   Traefik routes to; the public URL stays on 443.
2. Leave the domain fields for `pipeline` and `fundlens-postgres` empty. *Save*.

## 4. Bugsink project

1. Bugsink → team `neuroticsasquat.ch` → *New project*. Name `fundlens`. *Save*.
2. Project → *Alerts*: **Alert on new issue**, **Alert on regression** and **Alert on unmute** are on
   (the defaults).
3. *Add messaging service* → *Discord*. Name `Discord #alerts`, webhook URL from the vault item
   `Discord webhook #alerts`. *Save*, then *Send test message*.
4. Copy the DSN from the project's *SDK setup* page (`https://<key>@bugsink.neuroticsasquat.ch/<id>`) into
   the business-vault item `Bugsink DSNs`, field `fundlens`.

**Check:** the test message lands in Discord `#alerts`.

## 5. Kuma push monitors

In Kuma, for each row: *Add New Monitor*, then the row's settings.

| Field | `fundlens/weekly` | `fundlens/publish` |
| --- | --- | --- |
| Monitor Type | Push | Push |
| Friendly Name | `fundlens/weekly` | `fundlens/publish` |
| Heartbeat Interval | `648000` (7 d + 12 h, spec §10.3) | `648000` |
| Retries | `0` | `0` |
| Notifications | `Discord #alerts` | `Discord #alerts` |

Copy each push URL (`https://kuma.tail1afe5a.ts.net/api/push/<token>?status=up&msg=OK&ping=`) before you
*Save*. Paste it whole in step 6: the client replaces the query.

## 6. Environment variables

Coolify → the resource → *Environment Variables* (production). Coolify created an entry for every
`${NAME}` in the compose file when it loaded it. Set each value below, one at a time, and *Save*.

| Variable | Value |
| --- | --- |
| `POSTGRES_PASSWORD` | Generate on the laptop with `openssl rand -hex 32`. Hex only, because it is spliced into `DATABASE_URL`. Store it in the business vault as `fundlens Postgres` before pasting. |
| `R2_ENDPOINT` | `https://<account id>.r2.cloudflarestorage.com`, from NEU-2033's as-built section |
| `R2_ACCESS_KEY_ID` | The R2 read/write token's *Access Key ID* (NEU-2033) |
| `R2_SECRET_ACCESS_KEY` | The same token's *Secret Access Key* (NEU-2033) |
| `CLOUDFLARE_ZONE_ID` | The `fundlens.org` zone ID (NEU-2033) |
| `CLOUDFLARE_API_TOKEN` | The purge-only API token (NEU-2033) |
| `DEEPINFRA_API_KEY` | DeepInfra → *API keys* → *New API key*, named `fundlens` |
| `SENTRY_DSN` | The `fundlens` DSN from step 4 |
| `KUMA_PUSH_WEEKLY` | The `fundlens/weekly` push URL from step 5 |
| `KUMA_PUSH_PUBLISH` | The `fundlens/publish` push URL from step 5 |

These entries were seeded from the compose fallbacks. Leave them as they are: `R2_BUCKET=fundlens-data`,
`R2_PUBLIC_BUCKET=fundlens-public`, `LOG_LEVEL=INFO`, `ADJUDICATE_MODEL=deepseek-ai/DeepSeek-V4-Flash`,
`DUCKDB_MEMORY_LIMIT=28GB`, `DUCKDB_THREADS=6`,
`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector-b144lcfm2xe4mxo73dg7b8z9:4318`, and
`SERVICE_FQDN_API_8000`, which Coolify fills from step 3. `DATABASE_URL`, `DATA_DIR` and
`OTEL_RESOURCE_ATTRIBUTES` are literals in the compose file and have no entry.

**Check:** no entry in the list has an empty value except, at most, `SERVICE_FQDN_API_8000` before the
first deploy, and there is no entry named `SOURCE_COMMIT` or `OTEL_RESOURCE_ATTRIBUTES`. Either would
shadow what the compose file sets and turn `service.version` into `unknown`. Delete one if you find it.
If Coolify refuses because the name appears in the compose file, set its value to match the compose
file (ops `docs/runbooks/backend-telemetry-env.md`, §1 step 2).

## 7. Deploy

1. *Deploy*. Watch the deployment log to the end. The image builds once and serves `api` and `pipeline`.
2. On the host, name the three containers for the steps below:

   ```bash
   # laptop
   ssh hetzner-01
   ```

   ```bash
   # VM. Paste the UUID recorded in step 1.
   U=<resource uuid>
   API=$(docker ps --format '{{.Names}}' | grep "^api-$U")
   PIPE=$(docker ps --format '{{.Names}}' | grep "^pipeline-$U")
   PG=$(docker ps --format '{{.Names}}' | grep "^fundlens-postgres-$U")
   echo "$API $PIPE $PG"
   docker inspect -f '{{.State.Health.Status}}' "$API" "$PG"
   ```

**Expected:** three names, then `healthy` twice. `api` turns healthy only once `fundlens health` reaches
both Postgres and R2, so an R2 value from step 6 that is wrong shows up here as `unhealthy`; read why with
`docker exec "$PIPE" fundlens health`.

## 8. Check the environment inside the containers

```bash
# VM
docker exec "$API" printenv OTEL_RESOURCE_ATTRIBUTES
docker exec "$PIPE" printenv OTEL_RESOURCE_ATTRIBUTES
docker exec "$API" printenv SOURCE_COMMIT
docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$API"
docker exec "$PIPE" sh -c 'for v in DATABASE_URL R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY CLOUDFLARE_ZONE_ID CLOUDFLARE_API_TOKEN DEEPINFRA_API_KEY SENTRY_DSN KUMA_PUSH_WEEKLY KUMA_PUSH_PUBLISH DUCKDB_MEMORY_LIMIT DUCKDB_THREADS; do [ -n "$(printenv "$v")" ] || echo "EMPTY $v"; done; echo done'
docker exec "$API" sh -c 'for v in DATABASE_URL R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY SENTRY_DSN; do [ -n "$(printenv "$v")" ] || echo "EMPTY $v"; done; echo done'
```

**Expected:**

- Both `OTEL_RESOURCE_ATTRIBUTES` lines end in `service.version=<sha>`, where `<sha>` is the commit the
  deployment log names (and `git ls-remote https://github.com/neuroticsasquat-ch/fundlens main`), with
  `service.name=fundlens-api` and `service.name=fundlens-pipeline` respectively. `unknown` means step 2.1
  did not hold: set it again and redeploy.
- `SOURCE_COMMIT` prints the SHA, or `unknown` (see [Facts](#facts)). Write which in the Log. If it
  is `unknown` while `OTEL_RESOURCE_ATTRIBUTES` carries the SHA, that is a known deviation from
  NEU-2032's Definition of done ("`printenv SOURCE_COMMIT` in `api` is a real SHA"), as it was for
  NEU-1619. Record it in the Log as a deviation; the check that matters has passed.
- The network list includes `coolify`.
- Each loop prints only `done`. The loops print the names of empty variables, never values.

## 9. Migrate and check health

```bash
# VM
docker exec "$PIPE" alembic upgrade head
docker exec "$PG" psql -U fundlens -d fundlens -Atc "select count(*) from information_schema.tables where table_schema = 'app'"
docker exec "$PIPE" fundlens health; echo "exit=$?"
```

**Expected:** Alembic reaches head with no error; a table count above zero; `postgres: ok`, `r2: ok`,
`exit=0`.

## 10. Public endpoint and SigNoz

```bash
# laptop
curl -sS -o /dev/null -w '%{http_code}\n' https://api.fundlens.org/healthz
curl -sSI https://api.fundlens.org/healthz | grep -i '^server:'
```

**Expected:** `200`, then `server: cloudflare`. A `000` or a TLS error means the DNS record or the
certificate is not there yet: check NEU-2033's `api` record, then the deployment's Traefik logs.

Then SigNoz → *Services* (tailnet only): after a minute, `fundlens-api` is listed; one of its traces
shows `service.version=<sha>` and `deployment.environment=production`.

## 11. Crash reporting and the deadman

```bash
# VM
docker exec "$PIPE" fundlens crash-test; echo "exit=$?"
```

**Expected:** a traceback and `exit=1`. Then, within a minute:

- Bugsink → `fundlens`: a new issue ``RuntimeError: deliberate crash from `fundlens crash-test` ``, tag
  `pipeline_mode=crash-test`, release `<sha>`, environment `production`.
- Discord `#alerts`: the Bugsink alert for it, and Kuma's for `fundlens/weekly` going **down** with
  `crash-test: RuntimeError: deliberate crash …`. (Kuma has no `/fail` path; a failed step pushes
  `status=down`.)

Put the monitor back, and prove the publish monitor is reachable from the container too:

```bash
# VM
docker exec "$PIPE" fundlens crash-test --recover; echo "exit=$?"
docker exec "$PIPE" python -c "import os, urllib.request as u; print(u.urlopen(os.environ['KUMA_PUSH_PUBLISH'].split('?')[0] + '?status=up&msg=reachability').read())"
```

**Expected:** `exit=0` and `fundlens/weekly` back **up**; then `b'{"ok":true}'` and `fundlens/publish`
**up**. A timeout means the container cannot reach the tailnet (ops `docs/runbooks/tailnet.md`).

Then resolve the crash-test issue in Bugsink so a real crash later reads as new.

## 12. Pause both monitors until the schedule exists

Nothing pushes either monitor on a schedule until NEU-2063 adds the Coolify scheduled task, so both
would go red 7.5 days from now. In Kuma, open `fundlens/weekly` → *Pause*, and `fundlens/publish` →
*Pause*. NEU-2063 resumes them.

**Check:** both show *Paused* in Kuma's list.

## 13. Nightly backup (ops repo PR)

`backup-postgres.sh` already finds and dumps `fundlens-postgres` (it matches any container that sets
`PG_MAJOR`). Listing it in `REQUIRED_CONTAINERS`, so a night without it fails the run, needs a change in
the script itself: `REQUIRED_CONTAINERS` is matched against exact container names, and a compose app's
containers carry a deploy timestamp after the UUID that changes on every deploy.

1. In the ops repo, on a branch, change the required-container check in `backups/backup-postgres.sh` to
   match by prefix, and add this container's prefix to the default:

   ```bash
   for r in $REQUIRED_CONTAINERS; do
     # Prefix match: a Coolify compose app's containers carry a deploy timestamp after the UUID.
     case " $CONTAINERS" in
       *" $r"*) ;;
       *) echo "Required postgres container $r not found"; FAILED="${FAILED:+$FAILED }$r(missing)" ;;
     esac
   done
   ```

   Then append this container's prefix to the default. It matches the name with or without the
   timestamp:

   ```bash
   REQUIRED_CONTAINERS=${REQUIRED_CONTAINERS:-"i61ipm60wus0vx3j64eprtal mqxxit45ifsivt17b5rl5d2s hindsight-db-fudpdra7nh10vyfyesl7n7lf fundlens-postgres-<resource uuid>"}
   ```

   In `backups/postgres.md`, give the `REQUIRED_CONTAINERS` row of the *Variables* table the same
   default, and add after the table's paragraph: "Each entry is matched as a prefix: a Coolify compose
   app's containers carry a deploy timestamp after the UUID." In `docs/runbooks/uptime-kuma-monitors.md`, add a
   `### fundlens` table under *Push monitors* with two rows: `fundlens/weekly` and `fundlens/publish`,
   Coolify task *none yet (NEU-2063)*, interval 7.5 d (648000 s), env vars `KUMA_PUSH_WEEKLY` and
   `KUMA_PUSH_PUBLISH`. Open the PR, link it from NEU-2032, and merge it.
2. Install it on the VM (ops `backups/postgres.md`, *Install on the VM*, step 1), then run it once:

   ```bash
   # VM, from the ops checkout at the merged commit
   sudo cp backups/backup-postgres.sh /usr/local/bin/backup-postgres.sh
   sudo chmod 755 /usr/local/bin/backup-postgres.sh
   sudo /usr/local/bin/backup-postgres.sh
   ls -la /var/backups/postgres/ | grep "fundlens-postgres-$U-"
   ```

**Expected:** `Backup complete`, a `fundlens-postgres-<uuid>…-<date>.sql.gz` dump in the listing, and
Kuma's `backups/postgres` monitor up.

**Before the backfill (M4):** the script dumps the whole cluster, `gold*` schemas included, and gold
reaches 10–30 GB (spec §3.4) although only `app` needs keeping (spec §10.4). The fundlens cluster then
needs dumping with `--exclude-schema='gold*'`; that is an ops change of its own.

## 14. Record what was built

Append a Log entry with: the date, the resource UUID, the deployed SHA, the `SOURCE_COMMIT` reading
from step 8, the Bugsink project ID, the ops PR, and any step that deviated.

## Log

<!-- Append entries below; never rewrite one. -->
