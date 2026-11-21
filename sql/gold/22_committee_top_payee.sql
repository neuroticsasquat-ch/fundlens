-- committee_top_payee (every-FEC-dollar spec §5.4, §5.5, ADR-0012): the 100 payees a committee paid
-- most in the cycle, grouped by payee_key, net as filed. Payee rows only: counted, with a key (a
-- row filed with no name has none), and not an in-kind outlay, which paid no one: the payee it
-- names gave the committee the goods. A key netting to $0 or less is left out. Ranked by amount,
-- then key. Each cycle is its own list.
--
-- name is the key's reported spelling with the most payee dollars across the cycle's payee rows,
-- then the one the most rows report, then the first in order, as committee_top_organization.name
-- is chosen: one name per key, whichever committee lists it.
--
-- payee_id is a payee page's address: the first 16 hexadecimal characters, lower case, of the
-- SHA-256 of payee_key. NULL for a key with no page: one more than half of whose payee dollars,
-- over every cycle in gold, are on person rows (payee_is_person), and some are. Its rows are listed
-- here all the same. A key whose payee dollars net to $0 or less over every cycle has no half to
-- weigh: it has a page unless its person rows net above $0, so a firm's key whose refunds
-- outweigh its payments is not taken for a person's. NEU-2155 adds the hand-kept list,
-- fec/payee_no_page.csv, to the keys with none, and builds `payee` by this same rule.
CREATE TABLE committee_top_payee AS
WITH paid AS (
    SELECT cycle, committee_id, payee_key, payee_name, payee_is_person, amount
    FROM silver.operating_expenditure
    WHERE counted AND payee_key IS NOT NULL AND NOT is_in_kind
),
spelling AS (
    SELECT cycle, payee_key, payee_name AS name
    FROM paid
    GROUP BY cycle, payee_key, payee_name
    QUALIFY row_number() OVER (
        PARTITION BY cycle, payee_key
        ORDER BY sum(amount) DESC, count(*) DESC, payee_name
    ) = 1
),
person_majority AS (
    SELECT payee_key
    FROM paid
    GROUP BY payee_key
    HAVING coalesce(sum(amount) FILTER (WHERE payee_is_person), 0) > 0.5 * sum(amount)
        AND coalesce(sum(amount) FILTER (WHERE payee_is_person), 0) > 0
),
ranked AS (
    SELECT
        cycle,
        committee_id,
        payee_key,
        sum(amount) AS amount,
        row_number() OVER (
            PARTITION BY cycle, committee_id ORDER BY sum(amount) DESC, payee_key
        ) AS rank
    FROM paid
    GROUP BY cycle, committee_id, payee_key
    HAVING sum(amount) > 0
)
SELECT
    ranked.committee_id,
    CAST(ranked.cycle AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.payee_key,
    CASE
        WHEN person_majority.payee_key IS NULL THEN left(sha256(ranked.payee_key), 16)
    END AS payee_id,
    spelling.name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
JOIN spelling USING (cycle, payee_key)
LEFT JOIN person_majority USING (payee_key)
WHERE ranked.rank <= 100;
