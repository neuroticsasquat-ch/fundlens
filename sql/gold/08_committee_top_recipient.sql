-- committee_top_recipient (spec §7.1): the 100 candidates and committees a committee gave most to,
-- ranked together by amount, then kind, then id, so the order is stable.
--
-- A candidate row (recipient_kind 'candidate') is the disbursement side of committee_transfer, the
-- giver's 24Ks, summed by the candidate each is credited to, a pair netting below 0 left out: it
-- is returned gifts, in committee_cycle.total_returned_by_candidates (NEU-2204), so the candidate
-- rows add up to total_to_candidates.
--
-- A committee row (recipient_kind 'committee', NEU-2057) is the giver's gifts to a committee,
-- summed by recipient, a recipient netting below 0 left out: the recipients' receipts from it
-- (an 18K to a party, a JFC's 18G to its participant, a PAC's gift to a super PAC) and its 24Ks
-- credited to no candidate (a 24K to a super PAC, NEU-2075). A gift to a candidate's committee is
-- filed twice, the giver's 24K and the recipient's 18K, and is counted once, from the 24K. A
-- receipt credited to a candidate the giver credited a 24K to is a twin, whatever its amount,
-- date or committee: giver and recipient date a gift days apart, split it by election, or name
-- another of the candidate's committees, so no closer match is safe, and the candidate's row
-- already holds the giver's gifts to them. A receipt credited to no candidate is the twin of the
-- giver's 24K to the same recipient for the same amount, the n-th such receipt by date paired
-- with the n-th such 24K, so a second gift of the same amount still counts; a 24K credited to no
-- candidate is counted in its twin's place. A recipient `cm` lacks has no page and is in no
-- committee row.
CREATE TABLE committee_top_recipient AS
WITH to_candidates AS (
    SELECT
        from_committee_id AS committee_id,
        'candidate' AS recipient_kind,
        candidate_id AS recipient_id,
        sum(amount) AS amount
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND candidate_id IS NOT NULL
    GROUP BY from_committee_id, candidate_id
    HAVING sum(amount) >= 0
),
gift AS (
    SELECT
        from_committee_id,
        to_committee_id,
        amount,
        candidate_id,
        row_number() OVER (
            PARTITION BY from_committee_id, to_committee_id, amount
            ORDER BY date, source_record_id
        ) AS nth
    FROM silver.committee_transfer
    WHERE side = 'disbursement' AND from_committee_id IS NOT NULL AND to_committee_id IS NOT NULL
),
receipt AS (
    SELECT
        from_committee_id,
        to_committee_id,
        amount,
        row_number() OVER (
            PARTITION BY from_committee_id, to_committee_id, amount
            ORDER BY date, source_record_id
        ) AS nth
    FROM silver.committee_transfer AS transfer
    WHERE side = 'receipt'
        AND from_committee_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1
            FROM silver.committee_transfer AS credited
            WHERE credited.side = 'disbursement'
                AND credited.from_committee_id = transfer.from_committee_id
                AND credited.candidate_id = transfer.candidate_id
        )
),
to_committees AS (
    SELECT
        committee_id,
        'committee' AS recipient_kind,
        recipient_id,
        sum(amount) AS amount
    FROM (
        SELECT
            receipt.from_committee_id AS committee_id,
            receipt.to_committee_id AS recipient_id,
            receipt.amount
        FROM receipt
        WHERE NOT EXISTS (
            SELECT 1
            FROM gift
            WHERE gift.from_committee_id = receipt.from_committee_id
                AND gift.to_committee_id = receipt.to_committee_id
                AND gift.amount = receipt.amount
                AND gift.nth = receipt.nth
        )
        UNION ALL
        SELECT from_committee_id, to_committee_id, amount
        FROM gift
        WHERE candidate_id IS NULL
    ) AS given
    WHERE recipient_id IN (SELECT committee_id FROM silver.committee)
    GROUP BY committee_id, recipient_id
    HAVING sum(amount) >= 0
),
ranked AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY committee_id ORDER BY amount DESC, recipient_kind, recipient_id
        ) AS rank
    FROM (
        SELECT * FROM to_candidates
        UNION ALL
        SELECT * FROM to_committees
    ) AS recipients
)
SELECT
    ranked.committee_id,
    CAST({cycle} AS INTEGER) AS cycle,
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
