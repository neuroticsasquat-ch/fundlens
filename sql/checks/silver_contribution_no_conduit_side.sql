-- No conduit's or intermediary's side of an earmark is counted: the recipient's own row is
-- (ADR-0004). A conduit's 24T never is. Nor is an intermediary's 24I, one whose OTHER_ID is a
-- committee of the cycle other than a conduit and its filer, when the recipient itemized the gift
-- too: a contribution to that committee, no refund or 24I, with the same name and amount, dated
-- within 30 days of it (NEU-2203). Nor is a conduit's refund of an earmark: a refund at a conduit
-- that mirrors no gift of the conduit's own in `indiv`, whoever gave it, by name and amount, as
-- `conduit_earmark_refund` reads them (NEU-2199). The bulk file and the contributions on the left,
-- so each join builds on the few 24Is.
WITH earmark AS (
    SELECT
        counted.source_record_id,
        counted.recipient_committee_id,
        indiv.OTHER_ID AS other_id,
        regexp_replace(upper(counted.contributor_name), '[^A-Z0-9]', '', 'g') AS name_key,
        counted.amount,
        counted.date
    FROM indiv
    JOIN (SELECT * FROM contribution WHERE transaction_type = '24I') AS counted
        ON indiv.SUB_ID = counted.source_record_id
    WHERE indiv.OTHER_ID <> counted.recipient_committee_id
        AND indiv.OTHER_ID IN (SELECT committee_id FROM committee WHERE NOT is_conduit)
),
own_gift AS (
    -- The conduit's own gifts as 04_contribution.sql's `conduit_earmark_refund` reads them: any
    -- `indiv` row at the conduit, whoever gave it, that is no memo line, 24T, line naming an
    -- earmark's recipient or refund.
    SELECT CMTE_ID, regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g') AS name_key,
        abs(TRANSACTION_AMT) AS amount
    FROM indiv
    WHERE CMTE_ID IN (SELECT committee_id FROM committee WHERE is_conduit)
        AND MEMO_CD IS DISTINCT FROM 'X'
        AND TRANSACTION_TP IS DISTINCT FROM '24T'
        AND NOT regexp_matches(coalesce(TRANSACTION_TP, ''), '^[24][0-9]Y$')
        AND NOT regexp_matches(coalesce(MEMO_TEXT, ''), 'EARMARKED FOR .*\(C[0-9]{{8}}\)')
)
SELECT transaction_type, source_record_id, recipient_committee_id, amount,
    NULL AS twin_record_id
FROM contribution
WHERE transaction_type = '24T'
UNION ALL
SELECT '24I', earmark.source_record_id, earmark.recipient_committee_id, earmark.amount,
    twin.source_record_id
FROM contribution AS twin
JOIN earmark
    ON twin.recipient_committee_id = earmark.other_id
    AND regexp_replace(upper(twin.contributor_name), '[^A-Z0-9]', '', 'g') = earmark.name_key
    AND twin.amount = earmark.amount
WHERE twin.transaction_type <> '24I'
    AND NOT regexp_matches(twin.transaction_type, '^[24][0-9]Y$')
    AND abs(twin.date - earmark.date) <= 30
UNION ALL
SELECT refund.transaction_type, refund.source_record_id, refund.recipient_committee_id,
    refund.amount, NULL
FROM contribution AS refund
WHERE regexp_matches(refund.transaction_type, '^[24][0-9]Y$')
    AND refund.recipient_committee_id IN (SELECT committee_id FROM committee WHERE is_conduit)
    AND NOT EXISTS (
        SELECT 1
        FROM own_gift
        WHERE own_gift.CMTE_ID = refund.recipient_committee_id
            AND own_gift.name_key
                = regexp_replace(upper(refund.contributor_name), '[^A-Z0-9]', '', 'g')
            AND own_gift.amount = abs(refund.amount)
    );
