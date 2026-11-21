-- payee (every-FEC-dollar spec §5.4, §5.5, ADR-0012): one row per payee key with a page, across
-- every cycle in gold. A payee is grouped by payee_key, a normalized name, and never resolved.
--
-- payee_row and payee_page outlive this file: committee_top_payee, payee_cycle, payee_top_payer
-- and search_entity's payee rows read them.
--
-- payee_row holds the payee rows: counted, with a key (a row filed with no name has none), and not
-- an in-kind outlay, which paid no one: the payee it names gave the committee the goods. A view,
-- not a table: every cycle's rows are read once per file that reads them, never held.
CREATE TEMP VIEW payee_row AS
SELECT
    cycle,
    committee_id,
    candidate_id,
    payee_key,
    payee_name,
    payee_city,
    payee_state,
    payee_is_person,
    amount
FROM silver.operating_expenditure
WHERE counted AND payee_key IS NOT NULL AND NOT is_in_kind;

-- payee_page: every key with a page, and its payee_id, the page's address: the first 16
-- hexadecimal characters, lower case, of the SHA-256 of payee_key (UTF-8). Deterministic, so a
-- payee keeps its address through every rebuild of gold, with no crosswalk; it changes only when
-- the key does.
--
-- A key has no page when more than half of its payee dollars, over every cycle in gold, are on
-- person rows (payee_is_person), and some are; or when the hand-kept list
-- `fec/payee_no_page.csv` (`payee_no_page`, which the loader registers) names it, a name that
-- names nobody: PETTY CASH, UNITEMIZED. A key whose payee dollars net to $0 or less over every
-- cycle has no half to weigh: it has a page unless its person rows net above $0, so a firm's key
-- whose refunds outweigh its payments is not taken for a person's. A key with no page is listed
-- under the committees that paid it all the same (committee_top_payee).
CREATE TEMP TABLE payee_page AS
SELECT payee_key, left(sha256(payee_key), 16) AS payee_id
FROM payee_row
WHERE payee_key NOT IN (SELECT payee_key FROM payee_no_page)
GROUP BY payee_key
HAVING NOT (
    coalesce(sum(amount) FILTER (WHERE payee_is_person), 0) > 0.5 * sum(amount)
    AND coalesce(sum(amount) FILTER (WHERE payee_is_person), 0) > 0
);

-- Each display column is the key's reported value of it with the most payee dollars over every
-- cycle, then the one the most rows report, then the first in order, as donor's are (v1 spec
-- §6.7): a column chosen alone, so the city may come from one spelling's rows and the name from
-- another's. UNPIVOT leaves out NULLs, so a column is NULL only when no row reports it.
-- total_all_cycles is the key's payee dollars, net as filed; first_cycle and last_cycle the first
-- and last cycle it was paid in.
CREATE TABLE payee AS
WITH variant AS (
    SELECT payee_key, field, value, sum(amount) AS amount, count(*) AS rows
    FROM payee_row
    SEMI JOIN payee_page USING (payee_key)
    UNPIVOT (value FOR field IN (payee_name, payee_city, payee_state))
    GROUP BY payee_key, field, value
),
display AS (
    SELECT
        payee_key,
        max(value) FILTER (WHERE field = 'payee_name') AS display_name,
        max(value) FILTER (WHERE field = 'payee_city') AS city,
        max(value) FILTER (WHERE field = 'payee_state') AS state
    FROM (
        SELECT payee_key, field, value
        FROM variant
        QUALIFY row_number() OVER (
            PARTITION BY payee_key, field ORDER BY amount DESC, rows DESC, value
        ) = 1
    )
    GROUP BY payee_key
),
totals AS (
    SELECT payee_key, sum(amount) AS total, min(cycle) AS first_cycle, max(cycle) AS last_cycle
    FROM payee_row
    SEMI JOIN payee_page USING (payee_key)
    GROUP BY payee_key
)
SELECT
    payee_page.payee_id,
    payee_page.payee_key,
    display.display_name,
    display.city,
    display.state,
    CAST(totals.total AS DECIMAL(16, 2)) AS total_all_cycles,
    CAST(totals.first_cycle AS INTEGER) AS first_cycle,
    CAST(totals.last_cycle AS INTEGER) AS last_cycle
FROM payee_page
JOIN totals USING (payee_key)
JOIN display USING (payee_key);
