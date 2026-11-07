-- committee_top_organization (spec §7.1, ADR-0011): the 100 organizations that gave most to a
-- committee in the cycle, grouped by organization_key, net of refunds; an organization whose gifts
-- net to nothing or less is left out, as top-donor lists leave such donors out, and so is a
-- receipt filed with no name, which has no key (it counts in committee_cycle all the same). Ranked
-- by amount, then key.
--
-- name is the key's reported spelling with the most money across the cycle's receipts (refunds
-- net out), then the one the most receipts report, then the first in order, as donor.display_name
-- is chosen (spec §6.7): one name per key, whichever committee lists it.
CREATE TABLE committee_top_organization AS
WITH spelling AS (
    SELECT organization_key, organization_name AS name
    FROM silver.organization_receipt
    WHERE organization_key IS NOT NULL
    GROUP BY organization_key, organization_name
    QUALIFY row_number() OVER (
        PARTITION BY organization_key
        ORDER BY sum(amount) DESC, count(*) DESC, organization_name
    ) = 1
),
given AS (
    SELECT recipient_committee_id AS committee_id, organization_key, sum(amount) AS amount
    FROM silver.organization_receipt
    WHERE organization_key IS NOT NULL
    GROUP BY recipient_committee_id, organization_key
    HAVING sum(amount) > 0
),
ranked AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY committee_id ORDER BY amount DESC, organization_key) AS rank
    FROM given
)
SELECT
    ranked.committee_id,
    CAST({cycle} AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.organization_key,
    spelling.name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
JOIN spelling USING (organization_key)
WHERE ranked.rank <= 100;
