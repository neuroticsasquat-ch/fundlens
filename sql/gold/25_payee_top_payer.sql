-- payee_top_payer (every-FEC-dollar spec §5.5, ADR-0012): the 100 committees that paid a payee
-- most in the cycle, its payee rows (payee_row, 22_payee.sql) net as filed; a committee netting to
-- $0 or less is left out. Ranked by amount, then committee_id. Each cycle is its own list; only a
-- payee with a page (payee_page) has one.
--
-- candidate_id is the candidate the rows are credited to (silver operating_expenditure's
-- candidate_id, contribution's credit rule): where a handoff credits a committee's rows to two,
-- the one with more of the amount, then the first in order; NULL when no row is credited to one.
CREATE TABLE payee_top_payer AS
WITH paid AS (
    SELECT payee_page.payee_id, payee_row.cycle, payee_row.committee_id, payee_row.candidate_id,
        sum(payee_row.amount) AS amount
    FROM payee_row
    JOIN payee_page USING (payee_key)
    GROUP BY ALL
),
credited AS (
    SELECT payee_id, cycle, committee_id, candidate_id
    FROM paid
    WHERE candidate_id IS NOT NULL
    QUALIFY row_number() OVER (
        PARTITION BY payee_id, cycle, committee_id ORDER BY amount DESC, candidate_id
    ) = 1
),
ranked AS (
    SELECT
        payee_id,
        cycle,
        committee_id,
        sum(amount) AS amount,
        row_number() OVER (
            PARTITION BY payee_id, cycle ORDER BY sum(amount) DESC, committee_id
        ) AS rank
    FROM paid
    GROUP BY payee_id, cycle, committee_id
    HAVING sum(amount) > 0
)
SELECT
    ranked.payee_id,
    CAST(ranked.cycle AS INTEGER) AS cycle,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.committee_id,
    credited.candidate_id,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
LEFT JOIN credited USING (payee_id, cycle, committee_id)
WHERE ranked.rank <= 100;
