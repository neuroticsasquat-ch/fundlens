-- Every top-spender row's amount is its line's net silver rows: the spender's spending of that
-- kind on that candidate of the race, on that side (every-FEC-dollar spec §6.5). Its side is NULL
-- for an electioneering communication and only for one, its kind one of the contract's four
-- names, and its spender a committee of the race's cycle.
SELECT
    listed.race_id,
    listed.rank,
    listed.committee_id,
    listed.candidate_id,
    listed.kind,
    listed.support_oppose,
    listed.amount,
    spent.amount AS silver_amount
FROM race_top_spender AS listed
LEFT JOIN (
    SELECT
        race_id,
        committee_id,
        candidate_id,
        CASE kind
            WHEN 'ie' THEN 'independent_expenditure'
            WHEN 'communication_cost' THEN 'communication_cost'
            WHEN 'coordinated' THEN 'party_coordinated'
        END AS kind,
        support_oppose,
        sum(amount) AS amount
    FROM silver.independent_expenditure
    WHERE race_id IS NOT NULL
    GROUP BY ALL
    UNION ALL
    SELECT
        race_id,
        committee_id,
        candidate_id,
        'electioneering_communication',
        CAST(NULL AS VARCHAR),
        sum(amount)
    FROM silver.electioneering_communication
    WHERE race_id IS NOT NULL
    GROUP BY ALL
) AS spent
    ON spent.race_id = listed.race_id
    AND spent.committee_id = listed.committee_id
    AND spent.candidate_id = listed.candidate_id
    AND spent.kind = listed.kind
    AND spent.support_oppose IS NOT DISTINCT FROM listed.support_oppose
WHERE spent.amount IS DISTINCT FROM listed.amount
    OR listed.kind NOT IN (
        'independent_expenditure', 'communication_cost', 'party_coordinated',
        'electioneering_communication'
    )
    OR (listed.kind = 'electioneering_communication') <> (listed.support_oppose IS NULL)
    OR listed.support_oppose NOT IN ('S', 'O')
    OR NOT EXISTS (
        SELECT 1
        FROM silver.committee AS committee
        JOIN race USING (cycle)
        WHERE race.race_id = listed.race_id AND committee.committee_id = listed.committee_id
    );
