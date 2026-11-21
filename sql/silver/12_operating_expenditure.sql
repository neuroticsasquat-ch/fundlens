-- operating_expenditure (every-FEC-dollar spec §5.1, §5.2, NEU-2152): one row per `oppexp` row,
-- a committee's operating expenditure as it itemized it on Schedule B, counted or not. Spending,
-- never a contribution and in no receipt total.
--
-- Rows. Every `oppexp` row filed by a committee of the cycle, read once (the view drops FEC's
-- repeated rows, NEU-2401), less:
--   - a row on a superseded filing: FILE_NUM in 04_contribution.sql's `superseded_filing`, the
--     receipt side's set, alone (spec §5.1, Decision 2). A payment-side rule would add filings
--     that are a different report repeating payments, not an amendment;
--   - a row whose filer `cm` lacks, as independent_expenditure's is (2024: 3 filers, 18 rows,
--     $121.7M, most of it one filer's four rows paid to itself).
-- No row is dropped as an overlap: no `oppexp` row is a `pas2`, `oth` or `indiv` row, nor a
-- committee transfer or independent expenditure (the measurement's Q7). Every sub-item and memo
-- row is kept, not counted but by rule 2 below, so the itemized list can show a card bill's
-- charges.
--
-- A sub-item (CONTEXT.md) is a row whose BACK_REF_TRAN_ID is the TRAN_ID of another row on its
-- committee and filing; parent_source_record_id is that row's SUB_ID, the lower one where the
-- filing holds the TRAN_ID twice. A row naming its own TRAN_ID is no sub-item (2024: 4 rows), and
-- its BACK_REF_TRAN_ID names nothing: so it is no in-kind outlay either, as the measurement,
-- which read such a reference as none, counted them. A row with no FILE_NUM is on no filing, so
-- it is no sub-item and no parent (2006 alone has such rows, 462 with none or 0; Q4c).
--
-- counted (§5.2), the one flag every total reads:
--   1. a sub-item is not counted, the middle of a chain among them: only a chain's top counts;
--   2. otherwise a row some sub-item names as its parent is counted, whatever its memo code;
--   3. otherwise a row is counted when MEMO_CD is not X.
-- Each amount is kept as filed, a negative one included (a refund, a correction, a payment moved
-- to Schedule E), so it nets out (§5.2, Decision 4).
--
-- The candidate is the one the paying committee raises for, by 04_contribution.sql's credit rule
-- (its `linked`, spelled again here): a principal (P) or authorized (A) committee's candidate, or
-- the candidate whose `cn` row names the committee principal; a handed-off committee's money is
-- the candidate it was handed from's before the handoff date and the other's on and after it, an
-- undated row the latter's (NEU-2126). A candidate alias is credited none.
--
-- payee_key is organization_key over the payee's name (§5.4, ADR-0012): exact grouping, no
-- linkage. The function is Python, so it runs once per distinct name, not per row; NULL for a
-- row with no name. payee_is_person: ENTITY_TP IND or CAN, or blank and the name one the
-- classifier (resolve.normalize.is_organization_name, NEU-2132) does not call an organization's,
-- asked once per distinct blank-typed name. is_in_kind: a row naming a TRAN_ID no row of its
-- filing holds (most name a receipt on it, Q7c), or a purpose saying IN-KIND; it keeps its
-- `counted`, and is in no payee figure.
--
-- spending_category and category_source are NULL until NEU-2153's classifier fills them.
CREATE TABLE operating_expenditure AS
WITH spending AS (
    SELECT
        *,
        nullif(trim(TRAN_ID), '') AS own_tran_id,
        -- A reference to the row's own TRAN_ID names no other row.
        nullif(nullif(trim(BACK_REF_TRAN_ID), ''), nullif(trim(TRAN_ID), '')) AS named_tran_id,
        -- FEC writes MM/DD/YYYY; a malformed date is null rather than a failed build. An
        -- impossible year (1201 to 9201 appear in every cycle) is kept as filed.
        CAST(try_strptime(TRANSACTION_DT, '%m/%d/%Y') AS DATE) AS spent_on
    FROM oppexp
    WHERE CMTE_ID IN (SELECT committee_id FROM committee)
        AND coalesce(FILE_NUM, 0) NOT IN (SELECT FILE_NUM FROM superseded_filing)
),
named AS (
    -- Every committee, filing and TRAN_ID some row names as its parent.
    SELECT DISTINCT CMTE_ID, FILE_NUM, named_tran_id
    FROM spending
    WHERE named_tran_id IS NOT NULL
),
parent AS (
    -- The row each name points to: the lower SUB_ID where a filing holds the TRAN_ID twice.
    SELECT spending.CMTE_ID, spending.FILE_NUM, spending.own_tran_id, min(spending.SUB_ID) AS SUB_ID
    FROM spending
    JOIN named
        ON named.CMTE_ID = spending.CMTE_ID
        AND named.FILE_NUM = spending.FILE_NUM
        AND named.named_tran_id = spending.own_tran_id
    GROUP BY spending.CMTE_ID, spending.FILE_NUM, spending.own_tran_id
),
linked AS (
    -- 04_contribution.sql's `linked`: see there for why each branch is as it is.
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
    SELECT committee_id, candidate_id, valid_from, valid_until
    FROM handoff_link
),
payee_name AS (
    SELECT NAME AS raw, organization_key(NAME) AS key
    FROM (SELECT DISTINCT NAME FROM spending WHERE NAME IS NOT NULL)
),
payee_class AS (
    SELECT NAME AS raw, is_organization_name(NAME) AS is_organization
    FROM (
        SELECT DISTINCT NAME
        FROM spending
        WHERE NAME IS NOT NULL AND nullif(trim(ENTITY_TP), '') IS NULL
    )
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    spending.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    spending.CMTE_ID AS committee_id,
    linked.candidate_id,
    spending.NAME AS payee_name,
    payee_name.key AS payee_key,
    spending.CITY AS payee_city,
    spending.STATE AS payee_state,
    spending.ZIP_CODE AS payee_zip,
    coalesce(
        trim(spending.ENTITY_TP) IN ('IND', 'CAN')
            OR (nullif(trim(spending.ENTITY_TP), '') IS NULL AND NOT payee_class.is_organization),
        false
    ) AS payee_is_person,
    spending.TRANSACTION_AMT AS amount,
    spending.spent_on AS date,
    spending.PURPOSE AS purpose,
    -- FEC's three-digit code, one written without its leading zeros ('1', '01') padded to it.
    CASE
        WHEN regexp_matches(trim(spending.CATEGORY), '^[0-9]{{1,2}}$')
            THEN lpad(trim(spending.CATEGORY), 3, '0')
        ELSE spending.CATEGORY
    END AS fec_category,
    NULL::VARCHAR AS spending_category,
    NULL::VARCHAR AS category_source,
    spending.TRANSACTION_PGI AS election_code,
    spending.RPT_TP AS report_type,
    spending.AMNDT_IND AS amendment_indicator,
    spending.MEMO_CD AS memo_code,
    spending.MEMO_TEXT AS memo_text,
    nullif(trim(spending.ENTITY_TP), '') AS entity_type,
    spending.TRAN_ID AS tran_id,
    spending.BACK_REF_TRAN_ID AS back_ref_tran_id,
    parent.SUB_ID AS parent_source_record_id,
    spending.IMAGE_NUM AS image_num,
    spending.FILE_NUM AS file_num,
    (spending.named_tran_id IS NOT NULL AND parent.SUB_ID IS NULL)
        OR coalesce(regexp_matches(upper(spending.PURPOSE), 'IN[- ]?KIND'), false) AS is_in_kind,
    CASE
        WHEN parent.SUB_ID IS NOT NULL THEN false
        WHEN spending.SUB_ID IN (SELECT SUB_ID FROM parent) THEN true
        ELSE spending.MEMO_CD IS DISTINCT FROM 'X'
    END AS counted
FROM spending
LEFT JOIN parent
    ON parent.CMTE_ID = spending.CMTE_ID
    AND parent.FILE_NUM = spending.FILE_NUM
    AND parent.own_tran_id = spending.named_tran_id
LEFT JOIN linked
    ON linked.committee_id = spending.CMTE_ID
    AND (linked.valid_from IS NULL OR spending.spent_on IS NULL
        OR spending.spent_on >= linked.valid_from)
    AND (linked.valid_until IS NULL OR spending.spent_on < linked.valid_until)
LEFT JOIN payee_name ON payee_name.raw = spending.NAME
LEFT JOIN payee_class ON payee_class.raw = spending.NAME;
