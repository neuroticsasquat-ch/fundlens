-- committee_transfer (spec §4, NEU-2039 §1.3): one row per `oth` receipt from another committee
-- and per `pas2` 24K committee-to-candidate contribution, told apart by `side`.
--
-- A committee's gift to a candidate's committee is reported twice: the giver files it in `pas2`
-- as a 24K (side = 'disbursement'), the recipient in `oth` as an 18K (side = 'receipt'). Both are
-- kept, and a gold aggregate sums one side only: receipts by to_committee_id or candidate_id,
-- disbursements by from_committee_id or candidate_id. Adding the two sides would count the gift
-- twice (expected.yaml's rule). The other `pas2` types (24A/24E independent expenditures, 24C
-- coordinated) are NEU-2057's independent_expenditure.
-- A negative amount is a correction, kept so it nets out. A conduit's 24K is no gift: it is the
-- conduit's side of an earmark it passed on (WinRed filed 348,042 in 2024, $10.2M net, most of them
-- refunds), an individual's money counted once on the recipient's `indiv` row (ADR-0004), so it
-- is dropped as the conduit's 24T is in 04_contribution.sql.
--
-- `oth` is not only receipts (NEU-2070). It also repeats every `pas2` row under the same SUB_ID,
-- holds the filer's own disbursements (24G, 22Z), the memo lines itemizing individuals' gifts
-- through a joint fundraising committee (15J, MEMO_CD = 'X') and candidates' loans to their
-- campaigns (16C). A receipt here is a receipt type (TRANSACTION_TP 1x, or 3x for a party's
-- convention, headquarters and recount accounts), not a memo line, from a giver whose id is a
-- committee's. A JFC's transfer is filed under any of several receipt types (18G mostly, some 18J,
-- a few 15J) and now and then with OTHER_ID blank: Trump's campaign filed $32.3M of its 2024 JFC
-- transfers so (NEU-2124). A blank OTHER_ID's giver is the joint fundraising committee (designation
-- J) its NAME names, compared as names are in 04_contribution.sql. Failing that, a row typed
-- PAC, COM, CCM or PTY (a committee by entity type) names the one `cm` committee its NAME is
-- (NEU-2131, ADR-0011); naming several, or none, it names no giver and the row is no receipt.
--
-- The same name-match rule reads `indiv` (NEU-2131): a counted row (contribution's rules: no memo
-- line, no 24T, no conduit's side, to a committee in `cm`) typed PAC, COM, CCM or PTY with a
-- blank OTHER_ID, whose NAME names exactly one `cm` committee, is a receipt from that committee,
-- under its own SUB_ID. In 2024 that is $635.3M that FEC itself counts as committee money
-- (Senate Leadership Fund's PAC-typed rows match FEC's figure to within $3); the $152.8M naming
-- several committees or none is dropped, from both files, and is no organization receipt either
-- (08_organization_receipt.sql). A row naming its own recipient names no giver. A row the rule
-- matches, in either file, is dropped when `oth` already holds the gift under the named
-- committee's id (`twin`: same recipient, giver, amount and date; 5 `indiv` rows, $70,000, in
-- 2024), so nothing is counted twice. A JFC named by NAME is NEU-2124's rule, not this one, and
-- has no twin rule. A matched row's amount is kept as filed, as every transfer's is.
--
-- A receipt's candidate is the one its recipient committee raises for, by contribution's rule
-- (NEU-2124), so a JFC's transfer to a campaign is that candidate's (gold's
-- total_jfc_transfers). A receipt to a committee raising for no candidate (a party, a PAC, a JFC)
-- has none: the giver's CAND_ID a 24K may fall back on is not on the receipt.
--
-- A 24K's candidate is the one its recipient committee is linked to (NEU-2075), the rule
-- contribution follows: givers often write a stale or wrong CAND_ID (a senator's old House id, an
-- id from an earlier race). Only when the recipient has no principal or authorized link to a
-- candidate of the cycle does the giver's CAND_ID stand, and only if it is one; otherwise the gift is
-- credited to no candidate, and is in neither a candidate's total_committee nor the giver's
-- total_to_candidates.
-- A giver's CAND_ID that is a candidate's alias (03_candidate_committee_link.sql, NEU-2127), often
-- the person's old id, stands for the id it is an alias of: an alias holds no money.
CREATE TABLE committee_transfer AS
WITH linked AS (
    -- As in 04_contribution.sql: a P or A link, or the candidate's `cn` principal committee; the
    -- principal link, then the lower candidate_id, so one each, or a handed-off committee's two
    -- dated rows. Only to a candidate of the cycle: `ccl` also links a few committees to
    -- candidates `cn` lacks (a handoff's are the cycle's, silver_handoff_linked.sql).
    (
        SELECT
            link.committee_id,
            link.candidate_id,
            NULL::DATE AS valid_from,
            NULL::DATE AS valid_until
        FROM candidate_committee_link AS link
        JOIN candidate USING (candidate_id)
        WHERE (link.designation IN ('P', 'A') OR link.committee_id = candidate.principal_committee_id)
            AND link.committee_id NOT IN (SELECT committee_id FROM handoff)
        QUALIFY row_number() OVER (
            PARTITION BY link.committee_id
            ORDER BY
                (link.designation = 'P' OR link.committee_id = candidate.principal_committee_id) DESC,
                link.candidate_id
        ) = 1
    )
    UNION ALL
    SELECT committee_id, candidate_id, valid_from, valid_until FROM handoff_link
),
jfc_named AS (
    -- Each JFC by name; a name two JFCs share names neither.
    SELECT
        regexp_replace(upper(name), '[^A-Z0-9]', '', 'g') AS name_key,
        min(committee_id) AS committee_id
    FROM committee
    WHERE designation = 'J'
    GROUP BY name_key
    HAVING count(*) = 1
),
cm_named AS (
    -- Each committee of the cycle by name, for a row typed PAC, COM, CCM or PTY with no
    -- committee id (NEU-2131); a name two committees share names neither.
    SELECT
        regexp_replace(upper(name), '[^A-Z0-9]', '', 'g') AS name_key,
        min(committee_id) AS committee_id
    FROM committee
    GROUP BY name_key
    HAVING count(*) = 1
),
receipt AS (
    SELECT
        oth.*,
        -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
        CAST(try_strptime(oth.TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date,
        coalesce(
            CASE WHEN trim(oth.OTHER_ID) LIKE 'C%' THEN trim(oth.OTHER_ID) END,
            jfc_named.committee_id,
            CASE
                WHEN trim(oth.ENTITY_TP) IN ('PAC', 'COM', 'CCM', 'PTY') THEN cm_named.committee_id
            END
        ) AS giver,
        -- The giver came from the name-match rule, not from OTHER_ID or the JFC rule.
        coalesce(trim(oth.OTHER_ID), '') = ''
            AND jfc_named.committee_id IS NULL
            AND trim(oth.ENTITY_TP) IN ('PAC', 'COM', 'CCM', 'PTY')
            AND cm_named.committee_id IS NOT NULL AS name_matched
    FROM oth
    LEFT JOIN jfc_named
        ON coalesce(trim(oth.OTHER_ID), '') = ''
        AND jfc_named.name_key = regexp_replace(upper(oth.NAME), '[^A-Z0-9]', '', 'g')
    LEFT JOIN cm_named
        ON coalesce(trim(oth.OTHER_ID), '') = ''
        AND cm_named.name_key = regexp_replace(upper(oth.NAME), '[^A-Z0-9]', '', 'g')
        AND cm_named.committee_id <> oth.CMTE_ID
    WHERE left(oth.TRANSACTION_TP, 1) IN ('1', '3') AND oth.MEMO_CD IS DISTINCT FROM 'X'
),
named_gift AS (
    -- A counted `indiv` row typed PAC, COM, CCM or PTY with no OTHER_ID, naming exactly one `cm`
    -- committee that is not its recipient. `indiv` on the left: the join builds on `cm_named`.
    SELECT
        indiv.SUB_ID,
        indiv.CMTE_ID,
        indiv.TRANSACTION_AMT,
        indiv.TRANSACTION_DT,
        indiv.TRANSACTION_TP,
        CAST(try_strptime(indiv.TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date,
        cm_named.committee_id AS giver
    FROM indiv
    JOIN cm_named ON cm_named.name_key = regexp_replace(upper(indiv.NAME), '[^A-Z0-9]', '', 'g')
    WHERE trim(indiv.ENTITY_TP) IN ('PAC', 'COM', 'CCM', 'PTY')
        AND coalesce(trim(indiv.OTHER_ID), '') = ''
        AND indiv.MEMO_CD IS DISTINCT FROM 'X'
        AND indiv.TRANSACTION_TP IS DISTINCT FROM '24T'
        AND NOT (
            indiv.CMTE_ID IN (SELECT committee_id FROM conduit)
            AND regexp_matches(coalesce(indiv.MEMO_TEXT, ''), 'EARMARKED FOR .*\(C[0-9]{{8}}\)')
        )
        AND indiv.CMTE_ID IN (SELECT committee_id FROM committee)
        AND cm_named.committee_id <> indiv.CMTE_ID
),
by_name AS (
    -- Every row the name-match rule gives a giver, from either file.
    SELECT SUB_ID, CMTE_ID, giver, TRANSACTION_AMT, TRANSACTION_DT
    FROM receipt
    WHERE name_matched
    UNION ALL
    SELECT SUB_ID, CMTE_ID, giver, TRANSACTION_AMT, TRANSACTION_DT
    FROM named_gift
),
twin AS (
    -- The name-matched rows whose gift `oth` holds under the giver's id already: dropped, so the
    -- gift is counted once. `oth` on the left: the join builds on the few name-matched rows.
    SELECT DISTINCT by_name.SUB_ID
    FROM oth
    JOIN by_name
        ON by_name.CMTE_ID = oth.CMTE_ID
        AND by_name.giver = trim(oth.OTHER_ID)
        AND by_name.TRANSACTION_AMT = oth.TRANSACTION_AMT
        AND by_name.TRANSACTION_DT = oth.TRANSACTION_DT
    WHERE left(oth.TRANSACTION_TP, 1) IN ('1', '3')
        AND oth.MEMO_CD IS DISTINCT FROM 'X'
        AND oth.SUB_ID <> by_name.SUB_ID
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    receipt.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    receipt.giver AS from_committee_id,
    receipt.CMTE_ID AS to_committee_id,
    linked.candidate_id,
    receipt.TRANSACTION_AMT AS amount,
    receipt.transaction_date AS date,
    receipt.TRANSACTION_TP AS transaction_type,
    'receipt' AS side
FROM receipt
LEFT JOIN linked
    ON linked.committee_id = receipt.CMTE_ID
    AND (linked.valid_from IS NULL OR receipt.transaction_date IS NULL
        OR receipt.transaction_date >= linked.valid_from)
    AND (linked.valid_until IS NULL OR receipt.transaction_date < linked.valid_until)
WHERE receipt.giver IS NOT NULL AND receipt.SUB_ID NOT IN (SELECT SUB_ID FROM twin)
UNION ALL
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    named_gift.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    named_gift.giver AS from_committee_id,
    named_gift.CMTE_ID AS to_committee_id,
    linked.candidate_id,
    named_gift.TRANSACTION_AMT AS amount,
    named_gift.transaction_date AS date,
    named_gift.TRANSACTION_TP AS transaction_type,
    'receipt' AS side
FROM named_gift
LEFT JOIN linked
    ON linked.committee_id = named_gift.CMTE_ID
    AND (linked.valid_from IS NULL OR named_gift.transaction_date IS NULL
        OR named_gift.transaction_date >= linked.valid_from)
    AND (linked.valid_until IS NULL OR named_gift.transaction_date < linked.valid_until)
WHERE named_gift.SUB_ID NOT IN (SELECT SUB_ID FROM twin)
UNION ALL
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    gift.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    gift.CMTE_ID AS from_committee_id,
    nullif(trim(gift.OTHER_ID), '') AS to_committee_id,
    coalesce(
        linked.candidate_id,
        stated.alias_of,
        stated.candidate_id
    ) AS candidate_id,
    gift.TRANSACTION_AMT AS amount,
    gift.transaction_date AS date,
    gift.TRANSACTION_TP AS transaction_type,
    'disbursement' AS side
FROM (
    SELECT *, CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date
    FROM pas2
    WHERE TRANSACTION_TP = '24K'
        AND CMTE_ID NOT IN (SELECT committee_id FROM committee WHERE is_conduit)
) AS gift
LEFT JOIN linked
    ON linked.committee_id = nullif(trim(gift.OTHER_ID), '')
    AND (linked.valid_from IS NULL OR gift.transaction_date IS NULL
        OR gift.transaction_date >= linked.valid_from)
    AND (linked.valid_until IS NULL OR gift.transaction_date < linked.valid_until)
LEFT JOIN candidate AS stated ON stated.candidate_id = gift.CAND_ID;
