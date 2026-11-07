-- jfc_attribution (spec §4, §6.11): one row per JFC attribution, an `oth` 15J memo line in which
-- a joint fundraising committee's participant itemizes an individual behind its share of a JFC
-- transfer (`jfc_line`, 04_contribution.sql). Evidence about a person, never money: the share
-- reaches the participant as the JFC's transfer in committee_transfer, and the JFC's own
-- `indiv` row counts the gift wherever the JFC itemized it, so no total reads `amount`. It is kept
-- as filed, with no refund sign rule.
--
-- The contributor columns and key are built exactly as contribution's, from the same
-- `contributor_*` tables, so 07_contributor.sql reduces both to one set of keys. The participant is
-- the filer, always known. The JFC is best effort: a line's OTHER_ID is always blank, so it is the
-- committee MEMO_TEXT names once a leading '<year> AGGREGATE;' and a 'JFC ATTRIB:', 'TRANSFER
-- FROM', 'JFC-', 'JFC:' or '*' prefix are stripped ('* HARRIS VICTORY FUND'), compared as names
-- are in 04_contribution.sql; else the one joint fundraising committee the filing (CMTE_ID and
-- FILE_NUM) reports a transfer from; else none. A JFC's transfer is filed under any of several
-- receipt types (18G mostly, some 18J, a few 15J), now and then with OTHER_ID blank (NEU-2124), so
-- the filing's transfers are its receipts in committee_transfer, by that table's giver rule, from a
-- committee of designation J (NEU-2183). Another committee's receipt in the filing, such as a
-- candidate's authorized committee's 18G, is no JFC transfer and is not counted.
CREATE TABLE jfc_attribution AS
WITH linked AS (
    -- As in 04_contribution.sql: a P or A link, or the candidate's `cn` principal committee; the
    -- principal link, then the lower candidate_id, so one each, or a handed-off committee's two
    -- dated rows.
    (
        SELECT
            link.committee_id,
            link.candidate_id,
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
    SELECT committee_id, candidate_id, valid_from, valid_until FROM handoff_link
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
    -- A filing's receipts from JFCs, when they all come from one. committee_transfer keeps no
    -- FILE_NUM, so a receipt is read back from its `oth` row.
    SELECT
        receipt.to_committee_id AS CMTE_ID,
        oth.FILE_NUM,
        min(receipt.from_committee_id) AS committee_id
    FROM committee_transfer AS receipt
    JOIN oth ON oth.SUB_ID = receipt.source_record_id AND oth.CMTE_ID = receipt.to_committee_id
    WHERE receipt.side = 'receipt'
        AND receipt.from_committee_id IN (SELECT committee_id FROM committee WHERE designation = 'J')
    GROUP BY receipt.to_committee_id, oth.FILE_NUM
    HAVING count(DISTINCT receipt.from_committee_id) = 1
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
        ) AS memo_key,
        -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
        CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE) AS transaction_date
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
    line.transaction_date AS date
FROM line
LEFT JOIN named ON named.name_key = line.memo_key AND line.memo_key <> ''
LEFT JOIN sender ON sender.CMTE_ID = line.CMTE_ID AND sender.FILE_NUM = line.FILE_NUM
LEFT JOIN linked
    ON linked.committee_id = line.CMTE_ID
    AND (linked.valid_from IS NULL OR line.transaction_date IS NULL
        OR line.transaction_date >= linked.valid_from)
    AND (linked.valid_until IS NULL OR line.transaction_date < linked.valid_until)
LEFT JOIN contributor_name AS cname ON cname.raw = line.NAME
LEFT JOIN contributor_zip AS czip ON czip.raw = line.ZIP_CODE
LEFT JOIN contributor_employer AS cemployer ON cemployer.raw = line.EMPLOYER
LEFT JOIN contributor_occupation AS coccupation ON coccupation.raw = line.OCCUPATION;
