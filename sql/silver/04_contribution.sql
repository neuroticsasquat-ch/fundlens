-- contribution (spec §4): one row per counted `indiv` contribution.
--
-- Counted: a gift from an individual (IND) or a candidate (CAN); an organization's is not one.
-- FEC fills ENTITY_TP only on electronic filings since April 2002, so a blank one is an individual:
-- `indiv` holds individuals' contributions, and older cycles and paper filings would otherwise
-- count none. An earmark (ADR-0004) counts once, on the recipient side: the recipient's
-- MEMO_CD = 'X' memo line and the conduit's 24T row are dropped, and the conduit is kept on the
-- counted row as conduit_committee_id. A conduit also files some earmarks' own side as a plain
-- 15 whose MEMO_TEXT names the recipient ('EARMARKED FOR BIDEN FOR PRESIDENT (C00703975)'):
-- dropped as its 24T is. A gift to the conduit itself (ActBlue's tips, 'CONTRIBUTION TO ACTBLUE')
-- is an ordinary contribution, with no conduit. A gift to a committee missing from `cm` (a few
-- fringe filers) is dropped: it would belong to no committee (NEU-2070). A refund (a 2nY or 4nY
-- type: 22Y to an individual, 20Y, 21Y, 41Y, 42Y) is written by FEC as a positive amount; it is
-- kept with its sign turned, so it nets out of every total and a correction reversing a refund
-- (a negative one) adds back (NEU-2073).
--
-- Names are compared after uppercasing and dropping all but letters and digits, so punctuation
-- and spacing never decide a match: 'ACT BLUE' is 'ACTBLUE'.
CREATE TABLE contribution AS
WITH linked AS (
    -- The candidate a principal (P) or authorized (A) committee raises for; any other committee,
    -- a leadership PAC (D) among them, raises for none. Should `ccl` link one committee P or A to
    -- two candidates, the principal link and then the lower candidate_id is kept, so the key holds.
    SELECT link.committee_id, link.candidate_id, candidate.name
    FROM candidate_committee_link AS link
    LEFT JOIN candidate USING (candidate_id)
    WHERE link.designation IN ('P', 'A')
    QUALIFY row_number() OVER (
        PARTITION BY link.committee_id ORDER BY link.designation = 'P' DESC, link.candidate_id
    ) = 1
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
    SELECT *, regexp_replace(upper(coalesce(MEMO_TEXT, '')), '[^A-Z0-9]', '', 'g') AS memo_key
    FROM indiv
    WHERE coalesce(nullif(trim(ENTITY_TP), ''), 'IND') IN ('IND', 'CAN')
        AND MEMO_CD IS DISTINCT FROM 'X'
        AND TRANSACTION_TP IS DISTINCT FROM '24T'
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
    kept.CMTE_ID AS recipient_committee_id,
    linked.candidate_id,
    CASE
        WHEN regexp_matches(kept.TRANSACTION_TP, '^[24][0-9]Y$') THEN -kept.TRANSACTION_AMT
        ELSE kept.TRANSACTION_AMT
    END AS amount,
    -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
    CAST(try_strptime(kept.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date,
    kept.TRANSACTION_TP AS transaction_type,
    kept.ENTITY_TP AS entity_type,
    kept.RPT_TP AS report_type,
    kept.AMNDT_IND AS amendment_indicator,
    kept.MEMO_TEXT AS memo_text,
    kept.conduit_committee_id,
    -- A candidate's own money, loans included, to a committee raising for them: a CAN gift under
    -- the candidate's last name and first given name ('WHITLOCK, GORDON R. MR' is 'WHITLOCK,
    -- GORDON'). Money routed through a conduit is an earmark, never self-funding.
    coalesce(
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
    kept.IMAGE_NUM AS image_num,
    kept.FILE_NUM AS file_num
FROM kept
LEFT JOIN linked ON linked.committee_id = kept.CMTE_ID;
