-- race_top_spender (every-FEC-dollar spec §6.5, NEU-2168): the 100 biggest lines of outside
-- spending on a race, a line being one spender's spending of one kind on one candidate of the race,
-- on one side, every spender's as filed (a candidate's own campaign making a 24C too, Decision 7).
-- `kind` is the contract's name
-- (independent_expenditure, communication_cost, party_coordinated, electioneering_communication),
-- never silver's `kind`. support_oppose is S or O, always S for a party coordinated expenditure,
-- and NULL for an electioneering communication, whose filing says neither. A row with no side
-- (NEU-2165) is in no line. A line netting to $0 or less is left out. Ranked by amount, then
-- committee_id, candidate_id, kind and support_oppose, so the order is stable.
--
-- Every spender is a committee of the cycle in silver `committee`, a non-committee spender (type
-- I, C or E) too, so committee_id is always set and every row has a page; `name` is the spender's
-- as that cycle's `cm` names it, as race_top_committee's is. race_top_committee stands beside it
-- unchanged: its `ie` rows are a spender's independent expenditures on the race, both sides summed.
CREATE TABLE race_top_spender AS
WITH line AS (
    SELECT
        race_id,
        cycle,
        committee_id,
        candidate_id,
        CASE kind
            WHEN 'ie' THEN 'independent_expenditure'
            WHEN 'communication_cost' THEN 'communication_cost'
            WHEN 'coordinated' THEN 'party_coordinated'
        END AS kind,
        support_oppose,
        amount
    FROM silver.independent_expenditure
    WHERE race_id IS NOT NULL AND support_oppose IN ('S', 'O')
    UNION ALL
    SELECT
        race_id,
        cycle,
        committee_id,
        candidate_id,
        'electioneering_communication' AS kind,
        CAST(NULL AS VARCHAR) AS support_oppose,
        amount
    FROM silver.electioneering_communication
    WHERE race_id IS NOT NULL
),
net AS (
    SELECT race_id, cycle, committee_id, candidate_id, kind, support_oppose, sum(amount) AS amount
    FROM line
    GROUP BY ALL
    HAVING sum(amount) > 0
),
ranked AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY race_id
            ORDER BY amount DESC, committee_id, candidate_id, kind, support_oppose
        ) AS rank
    FROM net
)
SELECT
    ranked.race_id,
    CAST(ranked.rank AS INTEGER) AS rank,
    ranked.committee_id,
    committee.name,
    ranked.candidate_id,
    ranked.kind,
    ranked.support_oppose,
    CAST(ranked.amount AS DECIMAL(16, 2)) AS amount
FROM ranked
LEFT JOIN silver.committee AS committee USING (cycle, committee_id)
WHERE ranked.rank <= 100;
