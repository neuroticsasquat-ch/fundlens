-- committee_top_payee (every-FEC-dollar spec §5.4, §5.5, ADR-0012): the 100 payees a committee paid
-- most in the cycle, grouped by payee_key, net as filed. Payee rows only (payee_row,
-- 22_payee.sql): counted, with a key, and no in-kind outlay. A key netting to $0 or less is left
-- out. Ranked by amount, then key. Each cycle is its own list.
--
-- name is the key's reported spelling with the most payee dollars across the cycle's payee rows,
-- then the one the most rows report, then the first in order, as committee_top_organization.name
-- is chosen: one name per key, whichever committee lists it.
--
-- payee_id is the key's payee page's (payee_page, 22_payee.sql), NULL for a key with no page: a
-- person's, or one `fec/payee_no_page.csv` names. Its rows are listed here all the same.
CREATE TABLE committee_top_payee AS
WITH spelling AS (
    SELECT cycle, payee_key, payee_name AS name
    FROM payee_row
    GROUP BY cycle, payee_key, payee_name
    QUALIFY row_number() OVER (
        PARTITION BY cycle, payee_key
        ORDER BY sum(amount) DESC, count(*) DESC, payee_name
    ) = 1
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
    FROM payee_row
    GROUP BY cycle, committee_id, payee_key
    HAVING sum(amount) > 0
)
SELECT
    ranked.committee_id,
    CAST(ranked.cycle AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.payee_key,
    payee_page.payee_id,
    spelling.name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
JOIN spelling USING (cycle, payee_key)
LEFT JOIN payee_page USING (payee_key)
WHERE ranked.rank <= 100;
