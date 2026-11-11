-- contribution (spec §4): one row per counted `indiv` contribution.
--
-- Counted: a gift from an individual (IND) or a candidate (CAN); an organization's is not one. FEC
-- fills ENTITY_TP only on electronic filings since April 2002, so a blank one is an individual
-- unless the classifier (resolve.normalize.is_organization_name, the 2024 measurement's rule V8)
-- calls its name an organization's (NEU-2132): `indiv` holds individuals' contributions, and older
-- cycles and paper filings would otherwise count none, or count every organization's gift as a
-- person's. A classified row is an organization receipt or a committee's gift
-- (08_organization_receipt.sql, 05_committee_transfer.sql). A filled entity type is never
-- second-guessed. An earmark (ADR-0004) counts once, on the recipient side: the recipient's
-- MEMO_CD = 'X' memo line and the conduit's 24T row are dropped, and the conduit is kept on the
-- counted row as conduit_committee_id. A conduit also files some earmarks' own side as a plain 15
-- whose MEMO_TEXT names the recipient ('EARMARKED FOR BIDEN FOR PRESIDENT (C00703975)'): dropped as
-- its 24T is. A gift to the conduit itself (ActBlue's tips, 'CONTRIBUTION TO ACTBLUE') is an
-- ordinary contribution, with no conduit. A 24I is dropped only when it is an intermediary's side
-- of an earmark whose recipient itemized it too (`intermediary_earmark`, below): most 24Is are a
-- recipient's own earmark receipts, coded 24I (NEU-2203). A conduit's refund counts only when it
-- mirrors a gift of the conduit's own, a tip refunded (`conduit_earmark_refund`, below): any
-- other refunds an earmark, which counts at its recipient alone, so subtracting it at the conduit
-- takes away money never added (NEU-2199). A gift to a committee missing from `cm`
-- (a few fringe filers) is dropped: it would belong to no committee (NEU-2070). A refund (a 2nY or
-- 4nY type: 22Y to an individual, 20Y, 21Y, 41Y, 42Y) subtracts, so it nets out of every total.
-- Most filers write a refund positive, some negative, so its sign is not trusted: every refund
-- counts as -abs(amount), except a negative one mirroring a positive refund (`reversal`), which
-- reverses it and adds back (NEU-2073). A positive refund is reversed once, however many
-- negatives mirror it (NEU-2269).
--
-- Names are compared after uppercasing and dropping all but letters and digits, so punctuation
-- and spacing never decide a match: 'ACT BLUE' is 'ACTBLUE'.
-- Each contribution carries its contributor key (spec §6.1): its reported name, ZIP, employer and
-- occupation, each normalized by resolve.normalize. The normalizers are Python, so each distinct
-- value is normalized once, not each row: a cycle reports far fewer of each than it has rows. One
-- scan of `indiv` and the JFC attribution lines collects all four. The four `contributor_*` tables,
-- each a reported value and its normalized form, outlive this file: 06_jfc_attribution.sql and
-- 07_contributor.sql read them too. So does `organization_name_class`, the classifier's call on
-- each distinct name, which 05_committee_transfer.sql and 08_organization_receipt.sql read.
--
-- `handoff_link` is each handed-off committee (`handoff`, fec/handoffs.csv) linked twice, dated: to
-- the candidate it was handed from until the handoff date, and to the one it was handed to from
-- that date on (NEU-2126). FEC's files show a committee as it stands today, and `ccl` links Biden's
-- 2024 campaign, Harris's since he withdrew, to both, so neither candidate alone holds its money:
-- each contribution, transfer and JFC attribution is the candidate's whose dates hold its own.
-- One with no date is the committee's current holder's, the candidate it was handed to. The
-- three `linked` CTEs, here and in 05_committee_transfer.sql and 06_jfc_attribution.sql, take
-- these rows for a handed-off committee in place of its single undated link.
CREATE TEMP VIEW handoff_link AS
SELECT committee_id, from_candidate_id AS candidate_id, NULL::DATE AS valid_from,
    handoff_date AS valid_until
FROM handoff
UNION ALL
SELECT committee_id, to_candidate_id AS candidate_id, handoff_date AS valid_from,
    NULL::DATE AS valid_until
FROM handoff;

-- `jfc_line_reported` is every `oth` line a JFC attribution may be built from (spec §6.11): a 15J
-- memo line, where a joint fundraising committee's participant itemizes an individual (IND, or
-- blank as in `indiv`) behind its share of a JFC transfer, filed by a committee in `cm`. Its names
-- are classified with `indiv`'s; `jfc_line`, below, is these lines less the blank-type ones the
-- classifier calls an organization's.
CREATE TEMP VIEW jfc_line_reported AS
SELECT *
FROM oth
WHERE TRANSACTION_TP = '15J'
    AND MEMO_CD = 'X'
    AND coalesce(nullif(trim(ENTITY_TP), ''), 'IND') = 'IND'
    AND CMTE_ID IN (SELECT committee_id FROM committee);

CREATE TEMP TABLE contributor_value AS
SELECT NAME, ZIP_CODE, EMPLOYER, OCCUPATION
FROM (
    SELECT NAME, ZIP_CODE, EMPLOYER, OCCUPATION FROM indiv
    UNION ALL
    SELECT NAME, ZIP_CODE, EMPLOYER, OCCUPATION FROM jfc_line_reported
)
GROUP BY GROUPING SETS ((NAME), (ZIP_CODE), (EMPLOYER), (OCCUPATION));

CREATE TEMP TABLE contributor_name AS
SELECT NAME AS raw, normalize_name(NAME) AS name FROM contributor_value WHERE NAME IS NOT NULL;

-- The classifier's call on each distinct name, made once per name (NEU-2132). Only a row with a
-- blank entity type ever asks it.
CREATE TEMP TABLE organization_name_class AS
SELECT raw, is_organization_name(raw) AS is_organization FROM contributor_name;

-- The lines 06_jfc_attribution.sql builds a JFC attribution from. A classified line is in no
-- table: it was evidence about a person, and it is not about one.
CREATE TEMP VIEW jfc_line AS
SELECT *
FROM jfc_line_reported
WHERE nullif(trim(ENTITY_TP), '') IS NOT NULL
    OR NAME IS NULL
    OR NAME NOT IN (SELECT raw FROM organization_name_class WHERE is_organization);

CREATE TEMP TABLE contributor_zip AS
SELECT ZIP_CODE AS raw, zip5(ZIP_CODE) AS zip5 FROM contributor_value WHERE ZIP_CODE IS NOT NULL;

CREATE TEMP TABLE contributor_employer AS
SELECT EMPLOYER AS raw, normalize_employer(EMPLOYER) AS employer_norm
FROM contributor_value
WHERE EMPLOYER IS NOT NULL;

CREATE TEMP TABLE contributor_occupation AS
SELECT OCCUPATION AS raw, normalize_occupation(OCCUPATION) AS occupation_norm
FROM contributor_value
WHERE OCCUPATION IS NOT NULL;

DROP TABLE contributor_value;

-- A 24I is FEC's earmarked-intermediary-out code, but most 2024 filers write it on their own
-- receipts of earmarks through a conduit: OTHER_ID ActBlue or WinRed, or blank, 136,731 rows,
-- $4.17M, every one on Form 3X line 11(a)(i) (docs/measurements/summary-files-2024.md Q10).
-- Those are the recipient's row and count. A 24I whose OTHER_ID is a committee of the cycle
-- other than a conduit and its own filer is an intermediary's side: Senate Conservatives Fund,
-- House Freedom Fund and Club for Growth passing an individual's gift on to a candidate
-- (1,424 rows, $496,673). It is dropped, as a 24T is (ADR-0004), when the recipient itemized the
-- same gift: a row at the committee OTHER_ID names, not a memo line, refund, 24T or 24I, with
-- the same name, compared as names are, and amount, dated within 30 days of it, since a
-- recipient often dates the receipt later (262 rows, $235,403). One the recipient did not
-- itemize is the only record of the gift, and counts. 05_committee_transfer.sql and
-- 08_organization_receipt.sql drop these rows too. `indiv` is on the left of the join, so it
-- builds on the few 24Is and reads `indiv` once more without holding it.
CREATE TEMP TABLE intermediary_earmark AS
WITH earmark AS (
    SELECT
        SUB_ID,
        OTHER_ID,
        regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g') AS name_key,
        TRANSACTION_AMT,
        CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date
    FROM indiv
    WHERE TRANSACTION_TP = '24I'
        AND MEMO_CD IS DISTINCT FROM 'X'
        AND OTHER_ID <> CMTE_ID
        AND OTHER_ID IN (SELECT committee_id FROM committee WHERE NOT is_conduit)
)
SELECT DISTINCT earmark.SUB_ID
FROM indiv AS twin
JOIN earmark
    ON twin.CMTE_ID = earmark.OTHER_ID
    AND regexp_replace(upper(twin.NAME), '[^A-Z0-9]', '', 'g') = earmark.name_key
    AND twin.TRANSACTION_AMT = earmark.TRANSACTION_AMT
WHERE twin.CMTE_ID IN (SELECT OTHER_ID FROM earmark)
    AND twin.MEMO_CD IS DISTINCT FROM 'X'
    AND coalesce(twin.TRANSACTION_TP, '') NOT IN ('24T', '24I')
    AND NOT regexp_matches(coalesce(twin.TRANSACTION_TP, ''), '^[24][0-9]Y$')
    AND abs(CAST(try_strptime(twin.TRANSACTION_DT, '%m%d%Y') AS DATE) - earmark.transaction_date)
        <= 30;

-- A conduit's refund of an earmark (NEU-2199). A conduit refunds the earmarks it passed on, and
-- the recipient's own refund nets the gift where it counted, so the conduit's must not subtract
-- it again: WinRed's 1,067,143 refunds in 2024 (-$55.6M, every MEMO_TEXT blank) against its own
-- $7.4M of tips left its total_individual at -$48.2M. A refund at a conduit is kept only when it
-- mirrors a gift of the conduit's own (no memo line, 24T or line naming an earmark's recipient),
-- a tip, whoever gave it, by name key and amount, whatever sign either was written in; any other
-- is dropped, with the reversal of one. The match is within the cycle: a tip refunded the cycle
-- after it was given mirrors nothing, and is dropped. On 2024 that drops 888,156 of WinRed's
-- (-$54.1M) and 65 of ActBlue's 72, and keeps 178,987 ($1.5M) of WinRed's, almost all $1 to $10:
-- measured on FEC's file, WinRed nets $5.9M, ActBlue $26.6M
-- (docs/measurements/summary-files-2024.md Q12).
-- Matching a refund to the conduit's dropped 24T or 15 instead leaves WinRed at -$20.6M, since it
-- itemizes the side of only 660,255 of its earmarks; dropping the refunds of givers with no gift
-- of their own there leaves it at -$14.9M, since most of its givers tip it too. Dropping every
-- conduit refund would drop the refunded tips, which are real. 05_committee_transfer.sql and
-- 08_organization_receipt.sql drop these rows too.
CREATE TEMP TABLE conduit_earmark_refund AS
WITH at_conduit AS (
    SELECT
        SUB_ID,
        CMTE_ID,
        regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g') AS name_key,
        abs(TRANSACTION_AMT) AS amount,
        regexp_matches(coalesce(TRANSACTION_TP, ''), '^[24][0-9]Y$') AS is_refund
    FROM indiv
    WHERE CMTE_ID IN (SELECT committee_id FROM conduit)
        AND MEMO_CD IS DISTINCT FROM 'X'
        AND TRANSACTION_TP IS DISTINCT FROM '24T'
        AND NOT regexp_matches(coalesce(MEMO_TEXT, ''), 'EARMARKED FOR .*\(C[0-9]{{8}}\)')
)
SELECT refund.SUB_ID
FROM at_conduit AS refund
WHERE refund.is_refund
    AND NOT EXISTS (
        SELECT 1
        FROM at_conduit AS own
        WHERE NOT own.is_refund
            AND own.CMTE_ID = refund.CMTE_ID
            AND own.name_key = refund.name_key
            AND own.amount = refund.amount
    );

-- A filing superseded by a later amendment that FEC's bulk file kept beside it (NEU-2196). FEC
-- keeps only a report's newest version, but an amendment that changes the form (F3X to F3, F3 to
-- F3P), the report type (12S to 12G, Q1 to TER, Q2 to 30S) or the coverage end reads to it as a new
-- report, so both stay in `indiv` and every gift on them counts twice: 2024's Newsom for California
-- Governor 2022 (C00836353) by $8.9M, $3.4M of it on line 11(a)(i). FEC publishes no bulk filing
-- index to say which filing amends which, so the bulk file decides: an electronic filing (FILE_NUM
-- above 0) is superseded when a later-numbered one at the same committee, itself an amendment
-- (AMNDT_IND 'A'), repeats at least half of its rows. A row repeats one when a row there has the
-- same gift: name (compared as names are), ZIP5, employer, occupation, amount and date. An undated
-- row repeats none. Against FEC's own index (OpenFEC's amendment_chain) on 2024 this takes 28 of
-- the 31 filings FEC says a later twin amends, and none of the 208 it says no filing amends
-- (docs/measurements/summary-files-2024.md Q13). The three it misses had most of their rows changed
-- by the amendment. Half, not any: a big filing and a later amendment of another report can share a
-- few same-day gifts of the same size, and both are real. Repeats within one filing are separate
-- gifts, each with its own TRAN_ID, and count (Q13).
-- FEC's committee_summary counts most such pairs twice too: Newsom's INDV_ITEM_CONTB is the two
-- filings' line 11(a)(i) added together. So a committee with a superseded filing sits below that
-- figure by design: a gift counts once.
-- A superseded filing's `indiv` rows are counted nowhere: not here, in 05_committee_transfer.sql or
-- in 08_organization_receipt.sql (a row with no FILE_NUM is on no superseded filing). Its `oth`
-- rows were not measured and are read as before. Built in three steps so `indiv` is never held: the
-- gifts on more than one filing (a hash of the committee and gift, grouped), then each filing's
-- rows and its rows holding such a gift, then the pairs.
CREATE TEMP VIEW filed_gift AS
SELECT
    CMTE_ID,
    FILE_NUM,
    AMNDT_IND,
    CASE
        WHEN try_strptime(TRANSACTION_DT, '%m%d%Y') IS NOT NULL THEN hash(
            CMTE_ID,
            regexp_replace(upper(coalesce(NAME, '')), '[^A-Z0-9]', '', 'g'),
            left(ZIP_CODE, 5),
            upper(EMPLOYER),
            upper(OCCUPATION),
            TRANSACTION_AMT,
            TRANSACTION_DT
        )
    END AS gift
FROM indiv
WHERE MEMO_CD IS DISTINCT FROM 'X' AND TRANSACTION_TP IS DISTINCT FROM '24T' AND FILE_NUM > 0;

CREATE TEMP TABLE repeated_gift AS
SELECT gift
FROM filed_gift
WHERE gift IS NOT NULL
GROUP BY gift
HAVING min(FILE_NUM) <> max(FILE_NUM);

-- One row per filing and repeated gift on it, and one per filing for its other rows (gift NULL).
CREATE TEMP TABLE filing_gift AS
SELECT
    filed_gift.CMTE_ID,
    filed_gift.FILE_NUM,
    bool_or(filed_gift.AMNDT_IND = 'A') AS is_amendment,
    repeated_gift.gift,
    count(*) AS rows
FROM filed_gift
LEFT JOIN repeated_gift ON repeated_gift.gift = filed_gift.gift
GROUP BY filed_gift.CMTE_ID, filed_gift.FILE_NUM, repeated_gift.gift;

CREATE TEMP TABLE superseded_filing AS
WITH filing AS (
    SELECT CMTE_ID, FILE_NUM, bool_or(is_amendment) AS is_amendment, sum(rows) AS rows
    FROM filing_gift
    GROUP BY CMTE_ID, FILE_NUM
)
SELECT DISTINCT earlier.FILE_NUM
FROM filing_gift AS earlier
JOIN filing_gift AS later
    ON later.CMTE_ID = earlier.CMTE_ID
    AND later.gift = earlier.gift
    AND later.FILE_NUM > earlier.FILE_NUM
JOIN filing AS amendment ON amendment.FILE_NUM = later.FILE_NUM AND amendment.is_amendment
JOIN filing AS original ON original.FILE_NUM = earlier.FILE_NUM
GROUP BY earlier.FILE_NUM, later.FILE_NUM, original.rows
HAVING sum(earlier.rows) * 2 >= original.rows;

-- A memo line that is the only record of a gift (NEU-2198). A partnership's, LLC's or trust's
-- gift is itemized as the entity's row with its members' shares as memo lines under it, and the
-- memo lines are dropped as attributions of a row that counts. But FEC's bulk file leaves out some
-- of those parent rows and keeps their memo lines: Fairshake's (C00835959) $68.4M from AH Capital
-- Management and five other firms is on its filings' line 11(a)(i), and in FEC's itemized figure,
-- with only the partners' memo lines in `indiv`. Such a line counts, as a gift of its own, when it
-- is shaped as an attribution and nothing it could be the attribution of is in either file:
--   - a gift typed 10 or 15, from an individual, organization or candidate (as `indiv` rows are
--     sorted below), of more than $0;
--   - its MEMO_TEXT says ATTRIBUTION ('PARTNERSHIP ATTRIBUTION', 'TRUST ATTRIBUTION'; never
--     REATTRIBUTION), or it has none, is typed 10 and is one of two or more names sharing its
--     filing, date and employer, which is not blank (a16z's partners at Fairshake carry no memo;
--     a blank employer says nothing of a firm);
--   - no row of `indiv` or `oth` on its filing, not a memo line, on its date or within one page
--     (IMAGE_NUM) of it, has its amount or its group's sum, the memo lines of its filing and date
--     from an organization, or from anyone else: a parent's row sits on its members' page or the
--     next (2,848 of 2,937 sampled parents), and bulk writes amounts in whole dollars, so a group's
--     sum may miss its parent's by up to $1 a line (TARGETED VICTORY's $500,000 is 3 x $166,666);
--   - no organization's memo line (of any type) on its filing, on its date or within a page, has
--     its amount or its group's sum, unless it is an organization's itself: a chain's top counts,
--     not the members whose shares it holds;
--   - no counted-shape row at its committee has its name, compared as names are, and amount: a
--     gift restated under a memo ('ORIGINAL CONTRIBUTION AS PREVIOUSLY REPORTED') counts already.
-- Any other memo line stays dropped: earmarks' (ADR-0004), JFC attributions, reattributions,
-- redesignations, loan conversions, and gifts noted elsewhere ('IN-KIND: STOCK TRANSFER, SEE
-- LINE 17'). The ticket's first cuts, any memo line on a page with no other row or with no row of
-- its amount or group's sum on its filing, were rejected: on 2024 they push 120 and 78 committees
-- more than 1% over FEC's itemized figure. This rule takes 1,041 lines, $127.7M, at 199
-- committees, and of the 192 with an itemized figure moves 186 toward it and pushes two more than
-- 1% over it ($53,200), partners' attributions of a parent that is itself a memo line bulk leaves
-- out (docs/measurements/summary-files-2024.md Q14). 05_committee_transfer.sql and
-- 08_organization_receipt.sql read these lines as counted rows too.
CREATE TEMP TABLE memo_line AS
SELECT
    SUB_ID,
    CMTE_ID,
    FILE_NUM,
    TRANSACTION_TP,
    TRANSACTION_AMT,
    regexp_replace(upper(coalesce(NAME, '')), '[^A-Z0-9]', '', 'g') AS name_key,
    upper(trim(coalesce(EMPLOYER, ''))) AS employer,
    upper(coalesce(MEMO_TEXT, '')) AS memo_text,
    trim(ENTITY_TP) IS NOT DISTINCT FROM 'ORG' AS is_organization,
    coalesce(nullif(trim(ENTITY_TP), ''), 'IND') IN ('IND', 'ORG', 'CAN') AS is_giver,
    CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date,
    TRY_CAST(IMAGE_NUM AS HUGEINT) AS page
FROM indiv
WHERE MEMO_CD = 'X' AND FILE_NUM IS NOT NULL;

-- The memo gifts, each with its group's sum and lines. Tables, not CTEs: DuckDB 2.0 reads a window
-- sum as 0 from a CTE read twice.
CREATE TEMP TABLE memo_gift AS
SELECT
    *,
    sum(TRANSACTION_AMT) OVER group_of AS group_amount,
    count(*) OVER group_of AS group_lines
FROM memo_line
WHERE TRANSACTION_TP IN ('10', '15') AND is_giver
WINDOW group_of AS (PARTITION BY CMTE_ID, FILE_NUM, transaction_date, is_organization);

CREATE TEMP TABLE attribution_shaped AS
SELECT memo_gift.*
FROM memo_gift
LEFT JOIN (
    SELECT CMTE_ID, FILE_NUM, transaction_date, employer, count(DISTINCT name_key) AS names
    FROM memo_gift
    GROUP BY ALL
) AS partners USING (CMTE_ID, FILE_NUM, transaction_date, employer)
WHERE TRANSACTION_AMT > 0
    AND (
        (regexp_matches(memo_text, '(^|[^E])ATTRIBUTION') AND NOT contains(memo_text, 'REATTRIBUT'))
        OR (
            trim(memo_text) = '' AND TRANSACTION_TP = '10' AND employer <> ''
            AND partners.names >= 2
        )
    );

CREATE TEMP TABLE orphaned_attribution AS
WITH filed AS (
    -- Every row, not a memo line, on a filing holding a shaped line: where its parent would be.
    SELECT CMTE_ID, FILE_NUM, TRANSACTION_AMT, TRANSACTION_DT, IMAGE_NUM
    FROM indiv
    WHERE MEMO_CD IS DISTINCT FROM 'X' AND FILE_NUM IN (SELECT FILE_NUM FROM attribution_shaped)
    UNION ALL
    SELECT CMTE_ID, FILE_NUM, TRANSACTION_AMT, TRANSACTION_DT, IMAGE_NUM
    FROM oth
    WHERE MEMO_CD IS DISTINCT FROM 'X' AND FILE_NUM IN (SELECT FILE_NUM FROM attribution_shaped)
),
parent AS (
    SELECT
        CMTE_ID,
        FILE_NUM,
        TRANSACTION_AMT,
        CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date,
        TRY_CAST(IMAGE_NUM AS HUGEINT) AS page,
        false AS is_memo
    FROM filed
    UNION ALL
    SELECT CMTE_ID, FILE_NUM, TRANSACTION_AMT, transaction_date, page, true
    FROM memo_line
    WHERE is_organization
),
attributes AS (
    -- The shaped lines with a parent. An organization's memo line is the parent of an individual's
    -- alone, never of its own or another organization's.
    SELECT DISTINCT shaped.SUB_ID
    FROM attribution_shaped AS shaped
    JOIN parent USING (CMTE_ID, FILE_NUM)
    WHERE NOT (parent.is_memo AND shaped.is_organization)
        AND (
            abs(parent.page - shaped.page) <= 1
            OR parent.transaction_date = shaped.transaction_date
        )
        AND (
            parent.TRANSACTION_AMT = shaped.TRANSACTION_AMT
            OR parent.TRANSACTION_AMT BETWEEN shaped.group_amount - shaped.group_lines
                AND shaped.group_amount + shaped.group_lines
        )
),
restated AS (
    -- A counted-shape row at the committee with the shaped line's name and amount. `indiv` is on
    -- the left, so the join builds on the few shaped lines.
    SELECT DISTINCT shaped.SUB_ID
    FROM indiv
    JOIN attribution_shaped AS shaped
        ON shaped.CMTE_ID = indiv.CMTE_ID
        AND shaped.TRANSACTION_AMT = indiv.TRANSACTION_AMT
        AND shaped.name_key
            = regexp_replace(upper(coalesce(indiv.NAME, '')), '[^A-Z0-9]', '', 'g')
    WHERE indiv.CMTE_ID IN (SELECT CMTE_ID FROM attribution_shaped)
        AND indiv.MEMO_CD IS DISTINCT FROM 'X'
        AND indiv.TRANSACTION_TP IS DISTINCT FROM '24T'
)
SELECT SUB_ID
FROM attribution_shaped
WHERE SUB_ID NOT IN (SELECT SUB_ID FROM attributes)
    AND SUB_ID NOT IN (SELECT SUB_ID FROM restated);

DROP TABLE attribution_shaped;
DROP TABLE memo_gift;
DROP TABLE memo_line;

CREATE TABLE contribution AS
WITH linked AS (
    -- The candidate a principal (P) or authorized (A) committee raises for; any other committee,
    -- a leadership PAC (D) among them, raises for none. The exception is the committee a
    -- candidate's `cn` row names principal (CAND_PCC), whatever `ccl` designates it: FEC's files
    -- show a committee as it stands today, and a campaign turned leadership PAC after the election
    -- raised the cycle's money as the campaign (Trump's 2024 C00828541, now NEVER SURRENDER, INC.,
    -- which `ccl` links N/D). Should `ccl` link one committee to two candidates, the principal link
    -- and then the lower candidate_id is kept, so the key holds; a committee handed from one to the
    -- other takes its two dated `handoff_link` rows instead, which never overlap.
    (
        SELECT
            link.committee_id,
            link.candidate_id,
            candidate.name,
            NULL::DATE AS valid_from,
            NULL::DATE AS valid_until
        FROM candidate_committee_link AS link
        LEFT JOIN candidate USING (candidate_id)
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
    SELECT handoff_link.committee_id, handoff_link.candidate_id, candidate.name,
        handoff_link.valid_from, handoff_link.valid_until
    FROM handoff_link
    LEFT JOIN candidate USING (candidate_id)
),
conduits AS (
    -- One row holding every conduit, so each contribution's MEMO_TEXT is searched for them
    -- without a join that would read `indiv` twice.
    SELECT list(
        struct_pack(committee_id, name := regexp_replace(upper(name), '[^A-Z0-9]', '', 'g'))
        ORDER BY committee_id
    ) AS named
    FROM conduit
),
individual AS (
    SELECT
        *,
        regexp_replace(upper(coalesce(MEMO_TEXT, '')), '[^A-Z0-9]', '', 'g') AS memo_key,
        -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
        CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date
    FROM indiv
    WHERE (
            trim(ENTITY_TP) IN ('IND', 'CAN')
            OR (
                nullif(trim(ENTITY_TP), '') IS NULL
                AND (
                    NAME IS NULL
                    OR NAME NOT IN (SELECT raw FROM organization_name_class WHERE is_organization)
                )
            )
        )
        AND (MEMO_CD IS DISTINCT FROM 'X' OR SUB_ID IN (SELECT SUB_ID FROM orphaned_attribution))
        AND TRANSACTION_TP IS DISTINCT FROM '24T'
        AND SUB_ID NOT IN (SELECT SUB_ID FROM intermediary_earmark)
        AND SUB_ID NOT IN (SELECT SUB_ID FROM conduit_earmark_refund)
        AND coalesce(FILE_NUM, 0) NOT IN (SELECT FILE_NUM FROM superseded_filing)
        AND NOT (
            CMTE_ID IN (SELECT committee_id FROM conduit)
            AND regexp_matches(coalesce(MEMO_TEXT, ''), 'EARMARKED FOR .*\(C[0-9]{{8}}\)')
        )
        AND CMTE_ID IN (SELECT committee_id FROM committee)
),
kept AS (
    SELECT
        individual.*,
        -- An earmark whose OTHER_ID is blank names its conduit only in MEMO_TEXT ('EARMARKED
        -- THROUGH WINRED'), by name or by FEC id; one naming two takes the lower id. A memo that
        -- says EARMARK but names no conduit gives none: there is no committee to record. Nor is
        -- a committee ever the conduit of a gift to itself.
        nullif(
            coalesce(
                by_id.committee_id,
                list_filter(
                    conduits.named,
                    lambda c: contains(individual.memo_key, c.name)
                        OR contains(individual.memo_key, c.committee_id)
                )[1].committee_id
            ),
            individual.CMTE_ID
        ) AS conduit_committee_id
    FROM individual
    CROSS JOIN conduits
    LEFT JOIN committee AS by_id
        ON by_id.committee_id = individual.OTHER_ID AND by_id.is_conduit
),
reversal AS (
    -- A negative refund that mirrors a positive one (same committee, donor and size) reverses it: a
    -- voided or uncashed refund check. It adds back, so the pair nets to nothing. Each positive
    -- refund is reversed once (NEU-2269): within a committee, donor and size, the negatives in
    -- order of date, then SUB_ID, reverse as many refunds as there are positive ones, and any
    -- further negative subtracts as every other refund does. Built from its own narrow scan of the
    -- refunds alone: a second reference to `individual` would make DuckDB materialize every
    -- contribution row, and run out of memory on a real cycle.
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
        FROM indiv
        WHERE regexp_matches(TRANSACTION_TP, '^[24][0-9]Y$') AND MEMO_CD IS DISTINCT FROM 'X'
            AND NAME IS NOT NULL
            AND coalesce(FILE_NUM, 0) NOT IN (SELECT FILE_NUM FROM superseded_filing)
    )
    SELECT SUB_ID
    FROM refund
    WHERE TRANSACTION_AMT < 0 AND nth <= positives
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    kept.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    -- The contributor as reported on this contribution, before resolution: what an itemized list
    -- shows, and what M3 reduces to contributor keys.
    kept.NAME AS contributor_name,
    kept.CITY AS contributor_city,
    kept.STATE AS contributor_state,
    kept.ZIP_CODE AS contributor_zip,
    kept.EMPLOYER AS contributor_employer,
    kept.OCCUPATION AS contributor_occupation,
    -- resolve.normalize.contributor_key, spelled in SQL: the four normalized values joined by '|',
    -- an absent one empty. A value `indiv` leaves blank normalizes to nothing, as a NULL does.
    concat_ws(
        '|',
        coalesce(cname.name.norm, ''),
        coalesce(czip.zip5, ''),
        coalesce(cemployer.employer_norm, ''),
        coalesce(coccupation.occupation_norm, '')
    ) AS contributor_key,
    kept.CMTE_ID AS recipient_committee_id,
    linked.candidate_id,
    CASE
        WHEN NOT regexp_matches(kept.TRANSACTION_TP, '^[24][0-9]Y$') THEN kept.TRANSACTION_AMT
        WHEN kept.SUB_ID IN (SELECT SUB_ID FROM reversal) THEN -kept.TRANSACTION_AMT
        ELSE -abs(kept.TRANSACTION_AMT)
    END AS amount,
    kept.transaction_date AS date,
    kept.TRANSACTION_TP AS transaction_type,
    kept.ENTITY_TP AS entity_type,
    kept.RPT_TP AS report_type,
    kept.AMNDT_IND AS amendment_indicator,
    kept.MEMO_TEXT AS memo_text,
    kept.conduit_committee_id,
    -- A candidate's own money, loans included. A 15C is, whatever its entity type, name or route
    -- (NEU-2194): FEC's "contribution from the candidate", on line 11(d), so the filer's choice of
    -- type is the evidence. 2024 files most of its own money typed IND or under a variant name
    -- ('MARYOTT - PERSONAL FUNDS, BRIAN', 'TORRESS, JERRY'), and some at a committee linked to no
    -- candidate, whose self_funding it is. Any other type is when it is a CAN gift to a committee
    -- raising for the candidate, under their last name and first given name ('WHITLOCK, GORDON R.
    -- MR' is 'WHITLOCK, GORDON'), and not routed through a conduit: that is an earmark.
    kept.TRANSACTION_TP IS NOT DISTINCT FROM '15C'
    OR coalesce(
        kept.ENTITY_TP = 'CAN'
        AND kept.conduit_committee_id IS NULL
        AND regexp_replace(upper(split_part(kept.NAME, ',', 1)), '[^A-Z0-9]', '', 'g')
            = regexp_replace(upper(split_part(linked.name, ',', 1)), '[^A-Z0-9]', '', 'g')
        AND regexp_replace(
            upper(split_part(trim(split_part(kept.NAME, ',', 2)), ' ', 1)), '[^A-Z0-9]', '', 'g'
        ) = regexp_replace(
            upper(split_part(trim(split_part(linked.name, ',', 2)), ' ', 1)), '[^A-Z0-9]', '', 'g'
        ),
        false
    ) AS is_self_funding,
    -- Money a hybrid PAC (CMTE_TP V or W) took into or refunded from its non-contribution account
    -- (NEU-2192): the account outside the contribution limits, whose receipts FEC types 10 (10J a
    -- JFC's share of them, 24I an earmark through a conduit whose memo begins "* NON-CONTRIBUTION
    -- ACCOUNT", NEU-2203, NEU-2207) and whose refunds 20Y, none of them on Form 3X line 11(a)(i).
    -- Kept, since donors gave it, and marked, so committee_cycle can keep it out of
    -- total_individual.
    -- A refund is judged by its type, not by matching it to a giver: most of a hybrid PAC's 20Ys
    -- name no one it holds a 10 from in the cycle (2024: $9.1M of the V and W committees' $9.7M),
    -- and a 22Y is a refund of an ordinary contribution even to someone who gave the other account
    -- too. At any other committee a 10 or a 20Y is ordinary money: a super PAC (O, U) reports its
    -- 10s on line 11(a)(i) and refunds them as 20Ys.
    coalesce(
        fec_line(kept.TRANSACTION_TP, recipient.type, kept.MEMO_TEXT)
            = 'non-contribution account',
        false
    ) AS is_non_contribution_account,
    -- The Form 3/3X line FEC files the row's type on (fec.lines, NEU-2193), and whether that is a
    -- line no total_individual counts: neither 11(a)(i), a candidate's 15C, a refund of either nor
    -- the non-contribution account, which has its own figure. A national party's convention,
    -- headquarters and recount accounts (30, 31, 32 and their variants, refunded as 40Y, 41Y,
    -- 42Y), a gift from an unregistered committee (18U) and a transfer (18G) are among them:
    -- kept, since donors gave them, and marked, so committee
    -- and candidate totals compare with FEC's itemized figure (INDV_ITEM_CONTB). A type the rule
    -- does not place counts, as every type did before it: `indiv` is individuals' contributions.
    fec_line(kept.TRANSACTION_TP, recipient.type, kept.MEMO_TEXT) AS fec_line,
    coalesce(
        fec_line(kept.TRANSACTION_TP, recipient.type, kept.MEMO_TEXT)
            NOT IN ('11(a)(i)', '11(d) candidate', '20 refunds', 'non-contribution account'),
        false
    ) AS is_other_line,
    kept.IMAGE_NUM AS image_num,
    kept.FILE_NUM AS file_num
FROM kept
JOIN committee AS recipient ON recipient.committee_id = kept.CMTE_ID
LEFT JOIN linked
    ON linked.committee_id = kept.CMTE_ID
    AND (linked.valid_from IS NULL OR kept.transaction_date IS NULL
        OR kept.transaction_date >= linked.valid_from)
    AND (linked.valid_until IS NULL OR kept.transaction_date < linked.valid_until)
LEFT JOIN contributor_name AS cname ON cname.raw = kept.NAME
LEFT JOIN contributor_zip AS czip ON czip.raw = kept.ZIP_CODE
LEFT JOIN contributor_employer AS cemployer ON cemployer.raw = kept.EMPLOYER
LEFT JOIN contributor_occupation AS coccupation ON coccupation.raw = kept.OCCUPATION;
