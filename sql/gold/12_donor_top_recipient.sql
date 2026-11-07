-- donor_top_recipient (spec §7.1): the 100 recipients a donor gave most to, over every cycle (this
-- build's one until NEU-2059). A gift to a committee raising for a candidate (silver's candidate_id)
-- is to the candidate; any other is to the committee. Self-funding is in: a candidate's own money
-- is a gift to their campaign, kept off the campaign's top donors only. A recipient the donor's
-- refunds net to nothing or less is left out. Ranked by amount, then id (a candidate's and a
-- committee's never coincide).
CREATE TABLE donor_top_recipient AS
WITH given AS (
    SELECT
        donor_id,
        CASE WHEN candidate_id IS NULL THEN 'committee' ELSE 'candidate' END AS recipient_kind,
        coalesce(candidate_id, recipient_committee_id) AS recipient_id,
        sum(amount) AS amount
    FROM silver.contribution
    WHERE donor_id IS NOT NULL
    GROUP BY ALL
    HAVING sum(amount) > 0
),
ranked AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY donor_id ORDER BY amount DESC, recipient_id) AS rank
    FROM given
)
SELECT
    ranked.donor_id,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.recipient_kind,
    ranked.recipient_id,
    coalesce(candidate.name, committee.name) AS name,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
LEFT JOIN silver.candidate AS candidate
    ON ranked.recipient_kind = 'candidate' AND candidate.candidate_id = ranked.recipient_id
LEFT JOIN silver.committee AS committee
    ON ranked.recipient_kind = 'committee' AND committee.committee_id = ranked.recipient_id
WHERE ranked.rank <= 100;
