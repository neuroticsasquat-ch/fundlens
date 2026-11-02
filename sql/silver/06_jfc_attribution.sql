-- jfc_attribution (spec §4, §6.11): one row per JFC attribution, an `oth` 15J memo line in which
-- a joint fundraising committee's participant itemizes an individual behind its share of a JFC
-- transfer (`jfc_line`, 04_contribution.sql). Evidence about a person, never money: the share
-- reaches the participant as the JFC's 18J transfer in committee_transfer, and the JFC's own
-- `indiv` row counts the gift wherever the JFC itemized it, so no total reads `amount`. It is kept
-- as filed, with no refund sign rule.
--
-- The contributor columns and key are built exactly as contribution's, from the same
-- `contributor_*` tables, so 07_contributor.sql reduces both to one set of keys. The participant is
-- the filer, always known. The JFC is best effort: a line's OTHER_ID is always blank, so it is the
-- committee MEMO_TEXT names once a leading '<year> AGGREGATE;' and a 'JFC ATTRIB:', 'TRANSFER
-- FROM', 'JFC-', 'JFC:' or '*' prefix are stripped ('* HARRIS VICTORY FUND'), compared as names
-- are in 04_contribution.sql; else the one committee the filing (CMTE_ID and FILE_NUM) reports an
-- 18J transfer from; else none.
CREATE TABLE jfc_attribution AS
WITH linked AS (
    -- As in 04_contribution.sql: a P or A link, or the candidate's `cn` principal committee; the
    -- principal link, then the lower candidate_id, so one each.
    SELECT link.committee_id, link.candidate_id
    FROM candidate_committee_link AS link
    LEFT JOIN candidate USING (candidate_id)
    WHERE link.designation IN ('P', 'A') OR link.committee_id = candidate.principal_committee_id
    QUALIFY row_number() OVER (
        PARTITION BY link.committee_id
        ORDER BY
            (link.designation = 'P' OR link.committee_id = candidate.principal_committee_id) DESC,
            link.candidate_id
    ) = 1
),
named AS (
    -- One committee per name: a JFC (designation J) first, then the lower id.
    SELECT regexp_replace(upper(name), '[^A-Z0-9]', '', 'g') AS name_key, committee_id
    FROM committee
    QUALIFY row_number() OVER (
        PARTITION BY name_key ORDER BY designation = 'J' DESC, committee_id
    ) = 1
),
sender AS (
    -- A filing's 18J transfers, when they all come from one committee in `cm`.
    SELECT CMTE_ID, FILE_NUM, min(trim(OTHER_ID)) AS committee_id
    FROM oth
    WHERE TRANSACTION_TP = '18J' AND MEMO_CD IS DISTINCT FROM 'X'
    GROUP BY CMTE_ID, FILE_NUM
    HAVING count(DISTINCT trim(OTHER_ID)) = 1
        AND min(trim(OTHER_ID)) IN (SELECT committee_id FROM committee)
),
line AS (
    SELECT
        *,
        regexp_replace(
            regexp_replace(
                regexp_replace(upper(trim(coalesce(MEMO_TEXT, ''))), '^[0-9]{{4}} AGGREGATE;\s*', ''),
                '^(JFC ATTRIB:|TRANSFER FROM|JFC-|JFC:|\*)\s*',
                ''
            ),
            '[^A-Z0-9]',
            '',
            'g'
        ) AS memo_key
    FROM jfc_line
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    line.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    line.NAME AS contributor_name,
    line.CITY AS contributor_city,
    line.STATE AS contributor_state,
    line.ZIP_CODE AS contributor_zip,
    line.EMPLOYER AS contributor_employer,
    line.OCCUPATION AS contributor_occupation,
    concat_ws(
        '|',
        coalesce(cname.name.norm, ''),
        coalesce(czip.zip5, ''),
        coalesce(cemployer.employer_norm, ''),
        coalesce(coccupation.occupation_norm, '')
    ) AS contributor_key,
    line.CMTE_ID AS participant_committee_id,
    coalesce(named.committee_id, sender.committee_id) AS jfc_committee_id,
    linked.candidate_id,
    line.TRANSACTION_AMT AS amount,
    -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
    CAST(try_strptime(line.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date
FROM line
LEFT JOIN named ON named.name_key = line.memo_key AND line.memo_key <> ''
LEFT JOIN sender ON sender.CMTE_ID = line.CMTE_ID AND sender.FILE_NUM = line.FILE_NUM
LEFT JOIN linked ON linked.committee_id = line.CMTE_ID
LEFT JOIN contributor_name AS cname ON cname.raw = line.NAME
LEFT JOIN contributor_zip AS czip ON czip.raw = line.ZIP_CODE
LEFT JOIN contributor_employer AS cemployer ON cemployer.raw = line.EMPLOYER
LEFT JOIN contributor_occupation AS coccupation ON coccupation.raw = line.OCCUPATION;
