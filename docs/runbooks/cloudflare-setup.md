# Runbook: Cloudflare setup

How to put `fundlens.org` on Cloudflare and create everything fundlens needs there (NEU-2033; spec
§10.2, §8, §3.2; ADR-0002, ADR-0003): the zone and its DNS, the two R2 buckets, the R2 and purge-only
API tokens, the SPA's Worker with Workers Builds and its custom domain, and the cache and rate-limit
rules for `api.fundlens.org`. Append to the [Log](#log) at the bottom; never rewrite it.

**Not in this runbook:** public access and the `data.fundlens.org` custom domain on `fundlens-public`
(NEU-2067), the Coolify side of `api.fundlens.org` ([coolify-setup.md](coolify-setup.md), NEU-2032).

## Order

This runbook and [coolify-setup.md](coolify-setup.md) interleave:

1. **Part A** below (steps 1–9): the zone, DNS, buckets, tokens, Worker and rules. Record every value
   in the [As built](#as-built) table as you go: the Coolify runbook reads its environment from there.
2. [coolify-setup.md](coolify-setup.md), all of it.
3. **Part B** below (steps 10–12): the checks that need the deployed `api` and `pipeline` containers.

## Before you start

- You can sign in to the Cloudflare account that holds the other NS zones, and to Namecheap, where
  `fundlens.org` is registered.
- The laptop has `dig` and `curl`.
- You can write to the business vault.

## As built

Fill this in during Part A, then commit it ([step 9](#9-record-the-as-built-values)). IDs and names only:
**no token value or secret goes in this file**; those live in the vault items named here.

| What | Value |
| --- | --- |
| Account ID | |
| Zone ID (`fundlens.org`) | |
| Cloudflare nameservers | |
| R2 endpoint (`R2_ENDPOINT`) | `https://<account id>.r2.cloudflarestorage.com` |
| R2 buckets | `fundlens-data` (private, location hint WEUR), `fundlens-public` (private until NEU-2067) |
| R2 token | `fundlens-pipeline`, Object Read & Write on both buckets; vault item `fundlens R2 token` |
| Purge token | `fundlens-purge`, Zone → Cache Purge on `fundlens.org`; vault item `fundlens Cloudflare purge token` |
| Worker | `fundlens`, custom domain `fundlens.org` |
| Cache rule | `api: cache everything, respect origin` |
| Rate-limit rule | `api: /v1 per IP` |

## Part A — setup

### 1. Add the zone

1. Cloudflare dashboard → *Add a domain* → `fundlens.org` → *Quick scan for DNS records* → *Continue* →
   plan **Free**.
2. On the record review page, delete every imported record. Namecheap's parking records (an apex `A`,
   a `www` `CNAME`) would block the Worker's custom domain in step 7, and nothing else uses the domain.
   *Continue*.
3. Copy the two nameservers Cloudflare assigns into the As built table.
4. Before switching, check that the domain has no DNSSEC at the registrar, which would make it
   unresolvable once the nameservers change:

   ```bash
   # laptop
   dig +short DS fundlens.org
   ```

   **Expected:** no output. If a DS record prints, turn DNSSEC off first: Namecheap → *Domain List* →
   `fundlens.org` → *Manage* → *Advanced DNS* → *DNSSEC* off, and wait for `dig` to print nothing.
5. Namecheap → *Domain List* → `fundlens.org` → *Manage* → *Nameservers* → **Custom DNS** → enter the
   two Cloudflare nameservers → save (the green tick).
6. Back in Cloudflare, *Check nameservers now*.

**Check** (propagation can take up to a few hours):

```bash
# laptop
dig +short NS fundlens.org
```

**Expected:** the two Cloudflare nameservers, and the zone's *Overview* says **Active**. Copy the
*Zone ID* and *Account ID* from the *Overview* page's *API* panel into the As built table.

### 2. SSL/TLS and the `api` record

1. Zone → *SSL/TLS* → *Overview* → *Configure* → **Custom SSL/TLS** → **Full (strict)** → *Save*.
   New zones start on *Automatic SSL/TLS*. The origin is Coolify's Traefik with a Let's Encrypt
   certificate, so Cloudflare can verify it.
2. Zone → *SSL/TLS* → *Edge Certificates* → **Always Use HTTPS** stays **off**. Traefik already
   redirects to HTTPS, and an edge redirect would send Let's Encrypt's HTTP-01 challenge to HTTPS
   before the origin has a certificate to answer it with.
3. Zone → *DNS* → *Records* → *Add record*: type `A`, name `api`, IPv4 `138.201.223.253` (the Coolify
   host, `music-box-dancer`), proxy status **Proxied**, TTL *Auto*. *Save*.

**Check:**

```bash
# laptop
dig +short api.fundlens.org
```

**Expected:** Cloudflare addresses (not `138.201.223.253`). `https://api.fundlens.org` answers only
after the Coolify runbook has deployed `api`.

### 3. R2 buckets

1. Account → *R2 Object Storage*. If R2 is not enabled on the account yet, enable it (it asks for a
   payment method; usage stays inside the free tier at first).
2. *Create bucket*: name `fundlens-data`, location **Provide a location hint → Western Europe (WEUR)**
   (the pipeline that reads and writes it runs in Germany), default storage class **Standard**.
   *Create bucket*. Leave public access and custom domains off.
3. *Create bucket*: name `fundlens-public`, location **Automatic**, storage class **Standard**.
   *Create bucket*. Leave public access off: NEU-2067 turns it on with the custom domain, once there
   is a snapshot to serve.

**Check:** *R2 Object Storage → Overview* lists both buckets, and each bucket's *Settings* shows
*Public access: Disabled*.

### 4. R2 API token

1. *R2 Object Storage → Overview* → *Manage API tokens* (*{} API*) → **Create Account API token**. An
   account token, not a user one, so it keeps working whoever later administers the account.
2. Name `fundlens-pipeline`. Permissions **Object Read & Write**. *Specify bucket(s)* → **Apply to
   specific buckets only** → `fundlens-data` and `fundlens-public`. TTL **Forever**. Client IP filtering
   off. *Create API Token*.
3. The next page shows the values once. Save **Access Key ID** and **Secret Access Key** in a new vault
   item `fundlens R2 token`, and the **S3 endpoint**
   (`https://<account id>.r2.cloudflarestorage.com`) in the As built table as `R2_ENDPOINT`.

**Check:** the vault item holds both values; the endpoint's account ID matches the As built table's.
The token itself is proven from the `pipeline` container in step 10.

### 5. Purge-only API token

1. Profile icon → *My Profile* → *API Tokens* → *Create Token* → *Custom token* → *Get started*.
2. Token name `fundlens-purge`. Permissions: **Zone** · **Cache Purge** · **Purge**. Zone resources:
   **Include** · **Specific zone** · `fundlens.org`. No IP filtering, no TTL. *Continue to summary* →
   *Create Token*.
3. Save the token in a new vault item `fundlens Cloudflare purge token`.

**Check:**

```bash
# laptop. read -s keeps the token out of the terminal and the shell history.
read -rs PURGE_TOKEN
curl -s -H "Authorization: Bearer $PURGE_TOKEN" https://api.cloudflare.com/client/v4/user/tokens/verify
```

**Expected:** `"success":true` and `"status":"active"`.

### 6. The Worker and Workers Builds

1. Account → *Workers & Pages* → *Create* → *Import a repository* → *GitHub*. If
   `neuroticsasquat-ch/fundlens` is not listed, *Add account / Configure* the Cloudflare GitHub app on
   the `neuroticsasquat-ch` organisation and give it the `fundlens` repository.
2. Select `neuroticsasquat-ch/fundlens` and set:

   | Setting | Value |
   | --- | --- |
   | Project name | `fundlens`. It must match `name` in `frontend/wrangler.jsonc`, or the build fails. |
   | Build command | `pnpm install --frozen-lockfile && pnpm build` |
   | Deploy command | `npx wrangler deploy` |
   | Non-production branch builds | **on** |
   | Non-production branch deploy command | `npx wrangler versions upload`. Set it explicitly: on the other NS Workers a preview build ran `npx wrangler preview`, which fails without a `previews` block in `wrangler.jsonc` (ops `docs/runbooks/frontend-workers-migration.md`, 2026-10-17). |
   | Root directory (*Advanced settings*) | `frontend` |

   *Deploy*. This first build runs before the variables below exist; step 9's PR rebuilds with them.
3. Worker `fundlens` → *Settings* → *Build*:
   - *Branch control*: production branch **`main`**.
   - *Build watch paths*: include `frontend/**`, exclude nothing. *Save*.
   - *Variables and secrets*: *Add* → type **Text**, name `VITE_API_BASE_URL`, value
     `https://api.fundlens.org`. Add a second, `NODE_VERSION` = `24` (spec §2; pins the build image's
     Node). *Save*. These are build variables: the bundle is static, so they are inlined at build time
     (an assets-only Worker refuses runtime variables anyway).
4. Worker `fundlens` → *Settings* → *Domains & Routes*: leave `workers.dev` and **Preview URLs**
   enabled. Preview builds are served from them.

**Check:** the Worker's *Deployments* tab shows the first build. Its log shows pnpm `12.16.1` (the
build image takes the version from `packageManager` in `frontend/package.json`, ahead of any
`PNPM_VERSION` variable) and `pnpm install --frozen-lockfile` completing.

### 7. Custom domain `fundlens.org`

1. Worker `fundlens` → *Settings* → *Domains & Routes* → *Add* → **Custom Domain** → `fundlens.org` →
   *Add domain*. Cloudflare creates the apex DNS record and its certificate.

**Check** (the certificate can take a few minutes):

```bash
# laptop
curl -sS -o /dev/null -w '%{http_code}\n' https://fundlens.org/
curl -sS -o /dev/null -w '%{http_code}\n' https://fundlens.org/race/2024/senate/MD
```

**Expected:** `200` twice; the second is the SPA fallback serving `index.html` for a client-side route.

### 8. Cache and rate-limit rules

1. Zone → *Caching* → *Cache Rules* → *Create rule*:
   - Name `api: cache everything, respect origin`.
   - *Custom filter expression*: **Hostname** · *equals* · `api.fundlens.org`.
   - *Cache eligibility*: **Eligible for cache**.
   - *Edge TTL*: **Use cache-control header if present, bypass cache if not**. Every API response
     sets `Cache-Control` (`public, max-age=3600, s-maxage=604800`; `no-store` on `/healthz` and server
     errors; `fundlens.api.cache`), so the origin decides and publish's zone purge clears it (spec §7.2).
   - *Browser TTL*: **Respect origin**.
   - *Deploy*.
2. Zone → *Security* → *Security rules* → *Create rule* → **Rate limiting rules**:
   - Name `api: /v1 per IP`.
   - *If incoming requests match*: **URI Path** · *starts with* · `/v1/`. The Free plan's rate-limiting
     rules can match only on path, not hostname; nothing on the apex Worker lives under `/v1/`, so the
     rule still covers only the API.
   - *With the same characteristics*: **IP**.
   - *When rate exceeds*: **100** requests per **10 seconds**. A page load is one or two API calls; this
     stops a scraper hammering the API, which the dataset (spec §9) exists to make unnecessary.
   - *Then take action*: **Block**, for **10 seconds**.
   - *Deploy*.

   The IP characteristic, the 10-second period and the 10-second block are the only values the Free
   plan offers; the request count is the one real choice.

**Check:** both rules show *Active* in their lists.

### 9. Record the as-built values

The DoD's preview check needs a PR that touches `frontend/`, and merging it rebuilds production with
the step 6 variables. Make that PR record where the frontend is deployed:

```bash
# laptop, in the repo
git switch main && git pull
git switch -c docs/NEU-2033-as-built
```

1. Fill in the [As built](#as-built) table above.
2. In `frontend/README.md`, under *Deploy*, add the line
   `As built: Worker \`fundlens\`, custom domain \`fundlens.org\` (docs/runbooks/cloudflare-setup.md).`
3. Commit both files, push, and open the PR into `main`.

**Expected:** the PR's *Workers Builds* check passes and links a preview URL
(`https://<version>-fundlens.<subdomain>.workers.dev`) that serves the SPA. Merge it, wait for the
Worker's *Deployments* tab to show the merge commit's build as active, then open `https://fundlens.org`
in a browser.

**Expected:** the page reads **Build** followed by the merge commit's first 7 characters (the SPA
renders it from `WORKERS_CI_COMMIT_SHA`, so `curl` of the HTML will not show it). Production was
rebuilt with the step 6 variables. The preview's API calls fail CORS (only `https://fundlens.org` is
allowed, spec §7.2); that is expected.

Now run [coolify-setup.md](coolify-setup.md), then come back for Part B.

## Part B — checks after the Coolify runbook

### 10. R2 from the `pipeline` container

```bash
# VM (ssh hetzner-01). U is the Coolify resource UUID from coolify-setup.md step 1.
U=<resource uuid>
PIPE=$(docker ps --format '{{.Names}}' | grep "^pipeline-$U")
docker exec "$PIPE" fundlens health; echo "exit=$?"
```

**Expected:** `postgres: ok`, `r2: ok`, `exit=0`. On `r2: unreachable (ClientError: … 403 …)`, open
the `fundlens-pipeline` token (step 4) and check `fundlens-data` is among its buckets. If it is, the
403 comes from `fundlens health`'s `HeadBucket` call, which Cloudflare's R2 docs do not list under
*Object Read & Write*: record it in the Log and file a ticket to switch the check to a one-key
`ListObjectsV2`, rather than widening the token to *Admin*.

### 11. The purge token can purge and cannot list buckets

```bash
# laptop. Paste the Zone ID and Account ID from the As built table.
read -rs PURGE_TOKEN
ZONE=<zone id>
ACCOUNT=<account id>
curl -s -X POST -H "Authorization: Bearer $PURGE_TOKEN" -H "Content-Type: application/json" \
  --data '{"purge_everything":true}' "https://api.cloudflare.com/client/v4/zones/$ZONE/purge_cache"
echo
curl -s -H "Authorization: Bearer $PURGE_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/r2/buckets"
echo
```

**Expected:** the purge answers `"success":true`; the bucket list answers `"success":false` with an
authentication error (code `10000`).

### 12. The API is cached at the edge

```bash
# laptop
curl -sSI https://api.fundlens.org/v1/meta | grep -i '^cf-cache-status'
curl -sSI https://api.fundlens.org/v1/meta | grep -i '^cf-cache-status'
curl -sSI https://api.fundlens.org/healthz | grep -i '^cf-cache-status'
```

**Expected:** `MISS` (or `EXPIRED`), then **`HIT`**, then `BYPASS` or `DYNAMIC` for `/healthz`, which
must never be cached.

Append a Log entry with the date, the values filled in, and any step that deviated.

## Log

<!-- Append entries below; never rewrite one. -->
