-- organization_receipt (spec §4, ADR-0011): one row per organization receipt, an itemized gift
-- to a committee from a giver that is neither an individual nor a committee: entity type ORG, in
-- `indiv` or in `oth`. Organization money, never a contribution: no candidate_id, no contributor
-- key, no donor_id, and 07_contributor.sql never reads it. The classifier (NEU-2132,
-- `organization_name_class` from 04_contribution.sql) adds the `indiv` rows whose blank entity
-- type it calls an organization, with `classified` true, less the ones naming exactly one `cm`
-- committee other than their recipient, by 05_committee_transfer.sql's name match: that
-- committee's gift, a transfer there, or dropped there when `oth` holds it already, so counted
-- once either way. PAC, COM, CCM and PTY rows are committees' money (05_committee_transfer.sql)
-- or dropped, in neither table.
--
-- From `indiv`: a counted row by contribution's rules (04_contribution.sql): no memo line
-- (MEMO_CD = 'X'), no conduit's 24T, no intermediary's 24I its recipient itemized too
-- (`intermediary_earmark`, NEU-2203), no conduit's own line for an earmark it passed on
-- (ADR-0004), no conduit's refund of an earmark (`conduit_earmark_refund`, NEU-2199), to a
-- committee in `cm` (NEU-2070). The 2024 measurement (NEU-2129) found no ORG row
-- on a conduit's side; the rule stands for other cycles. A refund (a 2nY or 4nY type) subtracts
-- whichever sign its filer wrote, and a negative refund mirroring a positive one reverses it and
-- adds back, as in contribution (NEU-2073): each positive refund once (NEU-2269).
--
-- From `oth`: a receipt (TRANSACTION_TP 1x or 3x, no memo line) from a giver with no committee
-- id: OTHER_ID blank or not C-prefixed (a C-prefixed id the cycle's `cm` lacks is still a
-- committee's, counted in committee_transfer), not already a transfer there (a blank OTHER_ID
-- naming a JFC, NEU-2124), not a 15J (evidence, jfc_attribution) and not a loan: a 16C, 16F or
-- 16G is credit or its repayment, not a gift. A blank entity type in `oth` is not classified.
-- A row mirroring a counted `indiv` row (same recipient, name key, amount and date) is read
-- once, from `indiv`: no `oth` organization receipt shares a SUB_ID with an `indiv` row, so
-- SUB_ID alone would miss it (2 rows, $133,900, in 2024).
--
-- organization_key groups one organization's receipts: normalize_employer over the reported name
-- (cleaned, legal form stripped, employer alias applied), or the cleaned name when that names
-- nothing (resolve.normalize.organization_key). Exact grouping, no linkage: 'KOCH INDUSTRIES,
-- INC.' and 'KOCH INDUSTRIES INC' are one key, and two spellings the rule leaves apart are two
-- organizations. The function is Python, so it runs once per distinct name, not per row.
CREATE TABLE organization_receipt AS
WITH individual AS (
    SELECT
        SUB_ID, CMTE_ID, NAME, CITY, STATE, ZIP_CODE, TRANSACTION_AMT, TRANSACTION_DT,
        TRANSACTION_TP, ENTITY_TP, RPT_TP, AMNDT_IND, MEMO_TEXT, IMAGE_NUM, FILE_NUM, OTHER_ID
    FROM indiv
    WHERE (
            trim(ENTITY_TP) = 'ORG'
            OR (
                nullif(trim(ENTITY_TP), '') IS NULL
                AND NAME IN (SELECT raw FROM organization_name_class WHERE is_organization)
            )
        )
        AND MEMO_CD IS DISTINCT FROM 'X'
        AND TRANSACTION_TP IS DISTINCT FROM '24T'
        AND SUB_ID NOT IN (SELECT SUB_ID FROM intermediary_earmark)
        AND SUB_ID NOT IN (SELECT SUB_ID FROM conduit_earmark_refund)
        AND NOT (
            CMTE_ID IN (SELECT committee_id FROM conduit)
            AND regexp_matches(coalesce(MEMO_TEXT, ''), 'EARMARKED FOR .*\(C[0-9]{{8}}\)')
        )
        AND CMTE_ID IN (SELECT committee_id FROM committee)
),
cm_named AS (
    -- Each committee of the cycle by name, as in 05_committee_transfer.sql.
    SELECT
        regexp_replace(upper(name), '[^A-Z0-9]', '', 'g') AS name_key,
        min(committee_id) AS committee_id
    FROM committee
    GROUP BY name_key
    HAVING count(*) = 1
),
classified_kept AS (
    -- The `indiv` rows less the classified ones the name match makes a committee's gift. Joined
    -- on the few organization rows, never on `indiv`.
    SELECT individual.*
    FROM individual
    LEFT JOIN cm_named
        ON nullif(trim(individual.ENTITY_TP), '') IS NULL
        AND coalesce(trim(individual.OTHER_ID), '') = ''
        AND cm_named.name_key = regexp_replace(upper(individual.NAME), '[^A-Z0-9]', '', 'g')
        AND cm_named.committee_id <> individual.CMTE_ID
    WHERE cm_named.committee_id IS NULL
),
other AS (
    SELECT
        SUB_ID, CMTE_ID, NAME, CITY, STATE, ZIP_CODE, TRANSACTION_AMT, TRANSACTION_DT,
        TRANSACTION_TP, ENTITY_TP, RPT_TP, AMNDT_IND, MEMO_TEXT, IMAGE_NUM, FILE_NUM,
        regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g') AS name_key
    FROM oth
    WHERE trim(ENTITY_TP) = 'ORG'
        AND left(TRANSACTION_TP, 1) IN ('1', '3')
        AND TRANSACTION_TP NOT IN ('15J', '16C', '16F', '16G')
        AND MEMO_CD IS DISTINCT FROM 'X'
        AND coalesce(trim(OTHER_ID), '') NOT LIKE 'C%'
        AND CMTE_ID IN (SELECT committee_id FROM committee)
        AND SUB_ID NOT IN (SELECT source_record_id FROM committee_transfer)
),
mirrored AS (
    -- The `oth` receipts a counted `indiv` row mirrors. Built as `reversal` is in
    -- 04_contribution.sql: `indiv` scanned once more, on the left, so the join builds its hash
    -- table on the few `oth` rows and never holds the bulk file.
    SELECT DISTINCT other.SUB_ID
    FROM indiv
    JOIN other
        ON other.CMTE_ID = indiv.CMTE_ID
        AND other.TRANSACTION_AMT = indiv.TRANSACTION_AMT
        AND other.TRANSACTION_DT = indiv.TRANSACTION_DT
        AND other.name_key = regexp_replace(upper(indiv.NAME), '[^A-Z0-9]', '', 'g')
    WHERE indiv.MEMO_CD IS DISTINCT FROM 'X'
        AND indiv.TRANSACTION_TP IS DISTINCT FROM '24T'
        AND indiv.SUB_ID NOT IN (SELECT SUB_ID FROM intermediary_earmark)
        AND indiv.SUB_ID NOT IN (SELECT SUB_ID FROM conduit_earmark_refund)
        AND NOT (
            indiv.CMTE_ID IN (SELECT committee_id FROM conduit)
            AND regexp_matches(coalesce(indiv.MEMO_TEXT, ''), 'EARMARKED FOR .*\(C[0-9]{{8}}\)')
        )
),
kept AS (
    -- Every organization receipt's row. Read again below by `reversal` and `organization_name`:
    -- unlike `indiv`, it holds the organization rows alone (18,336 in 2024), so DuckDB can
    -- materialize it.
    SELECT
        SUB_ID, CMTE_ID, NAME, CITY, STATE, ZIP_CODE, TRANSACTION_AMT, TRANSACTION_DT,
        TRANSACTION_TP, ENTITY_TP, RPT_TP, AMNDT_IND, MEMO_TEXT, IMAGE_NUM, FILE_NUM
    FROM classified_kept
    UNION ALL
    SELECT
        SUB_ID, CMTE_ID, NAME, CITY, STATE, ZIP_CODE, TRANSACTION_AMT, TRANSACTION_DT,
        TRANSACTION_TP, ENTITY_TP, RPT_TP, AMNDT_IND, MEMO_TEXT, IMAGE_NUM, FILE_NUM
    FROM other
    WHERE SUB_ID NOT IN (SELECT SUB_ID FROM mirrored)
),
reversal AS (
    -- A negative refund that mirrors a positive one (same committee, organization and size)
    -- reverses it: a voided or uncashed refund check, which adds back (NEU-2073). Each positive
    -- refund is reversed once, as in 04_contribution.sql (NEU-2269): the negatives in order of
    -- date, then SUB_ID, reverse as many as there are positive ones, and any further one subtracts.
    WITH refund AS (
        SELECT
            SUB_ID,
            TRANSACTION_AMT,
            row_number() OVER (
                PARTITION BY CMTE_ID, NAME, abs(TRANSACTION_AMT), TRANSACTION_AMT < 0
                ORDER BY try_strptime(TRANSACTION_DT, '%m%d%Y') NULLS LAST, SUB_ID
            ) AS nth,
            count(*) FILTER (WHERE TRANSACTION_AMT > 0)
                OVER (PARTITION BY CMTE_ID, NAME, abs(TRANSACTION_AMT)) AS positives
        FROM kept
        WHERE regexp_matches(TRANSACTION_TP, '^[24][0-9]Y$') AND NAME IS NOT NULL
    )
    SELECT SUB_ID
    FROM refund
    WHERE TRANSACTION_AMT < 0 AND nth <= positives
),
organization_name AS (
    SELECT NAME AS raw, organization_key(NAME) AS key
    FROM (SELECT DISTINCT NAME FROM kept WHERE NAME IS NOT NULL)
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    kept.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    kept.NAME AS organization_name,
    organization_name.key AS organization_key,
    kept.CITY AS city,
    kept.STATE AS state,
    kept.ZIP_CODE AS zip,
    kept.CMTE_ID AS recipient_committee_id,
    CASE
        WHEN NOT regexp_matches(kept.TRANSACTION_TP, '^[24][0-9]Y$') THEN kept.TRANSACTION_AMT
        WHEN kept.SUB_ID IN (SELECT SUB_ID FROM reversal) THEN -kept.TRANSACTION_AMT
        ELSE -abs(kept.TRANSACTION_AMT)
    END AS amount,
    -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
    CAST(try_strptime(kept.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    kept.TRANSACTION_TP AS transaction_type,
    kept.ENTITY_TP AS entity_type,
    kept.RPT_TP AS report_type,
    kept.AMNDT_IND AS amendment_indicator,
    kept.MEMO_TEXT AS memo_text,
    kept.IMAGE_NUM AS image_num,
    kept.FILE_NUM AS file_num,
    -- Filed with no entity type, so the classifier put it here; the `oth` rows are all ORG.
    nullif(trim(kept.ENTITY_TP), '') IS NULL AS classified,
    -- A hybrid PAC's non-contribution-account money, as in contribution (NEU-2192): a 10, 10J or
    -- 20Y to or from a committee typed V or W, or a 24I there whose memo begins
    -- "* NON-CONTRIBUTION ACCOUNT" (NEU-2207), kept out of
    -- committee_cycle.total_from_organizations.
    coalesce(
        fec_line(kept.TRANSACTION_TP, recipient.type, kept.MEMO_TEXT)
            = 'non-contribution account',
        false
    ) AS is_non_contribution_account,
    -- The Form 3/3X line FEC files the row's type on, and whether no total counts that line, as in
    -- contribution (NEU-2193, NEU-2205): a national party's convention, headquarters and recount
    -- accounts' 30, 31 and 32 and their variants (a tribe's 31T, a 32J) and their refunds, an
    -- 18U, a transfer. Kept, the organization's gift, and marked, so committee_cycle puts it in
    -- total_other_lines, not total_from_organizations: FEC files a party's accounts on line 17, and
    -- its itemized figure leaves them out.
    fec_line(kept.TRANSACTION_TP, recipient.type, kept.MEMO_TEXT) AS fec_line,
    coalesce(
        fec_line(kept.TRANSACTION_TP, recipient.type, kept.MEMO_TEXT)
            NOT IN ('11(a)(i)', '11(d) candidate', '20 refunds', 'non-contribution account'),
        false
    ) AS is_other_line
FROM kept
JOIN committee AS recipient ON recipient.committee_id = kept.CMTE_ID
LEFT JOIN organization_name ON organization_name.raw = kept.NAME;
