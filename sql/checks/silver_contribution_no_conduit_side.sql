-- No conduit's or intermediary's side of an earmark is counted: the recipient's own row is
-- (ADR-0004). A conduit's 24T never is. Nor is an intermediary's 24I, one whose OTHER_ID is a
-- committee of the cycle other than a conduit and its filer, when the recipient itemized the gift
-- too: a contribution to that committee, no refund or 24I, with the same name and amount, dated
-- within 30 days of it (NEU-2203). The bulk file and the contributions on the left, so each join
-- builds on the few 24Is.
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
    AND abs(twin.date - earmark.date) <= 30;
