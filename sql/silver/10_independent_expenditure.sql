-- independent_expenditure (spec §4, NEU-2057): one row per `pas2` row that is a committee's spending
-- for or against a candidate rather than a gift to one, and the 24/48-hour file's rows `pas2` does
-- not hold yet (every-FEC-dollar spec §6.2, §6.3; NEU-2165), below. `pas2`'s 24Ks, committees' contributions
-- to candidates, are committee_transfer's disbursements (05_committee_transfer.sql).
--
-- kind tells the rows apart, and only kind 'ie' is an independent expenditure: 24E for the
-- candidate (support_oppose 'S') and 24A against (support_oppose 'O'). The rest are kept for the
-- outside-spending tickets (NEU-2167), in no total yet: a party's coordinated expenditure (24C,
-- 'coordinated', for its candidate) and a Form 7 filer's communication cost (24F for, 24N against,
-- 'communication_cost').
--
-- A memo line (MEMO_CD 'X') is no expenditure: it notes an unpaid invoice or debt (Schedule D),
-- itemizes a credit card's or vendor's payment, or restates an in-kind gift, and is dropped as
-- every other file's memo lines are. 2024's are 8,478 IE lines, $74,904,053, against 73,825 counted
-- IEs, $4,422,471,620. A row whose filer `cm` lacks is dropped as a contribution to one is (none
-- in 2024).
--
-- The candidate is CAND_ID's, or the id it is an alias of (NEU-2127), when it is a candidate of the
-- cycle; else none. CAND_ID is FEC's coding of the candidate the filing names, and is sometimes
-- another's, mostly where FEC recodes a correct filed id, now and then a filer's wrong id (the
-- filed name wins): Future Forward's three 2024 lines against TRUMP, filed with his id, are Biden's
-- in `pas2`. A row listed in `ie_candidate_correction`
-- (fec/ie_candidate_corrections.csv, NEU-2279) names the candidate its filing names instead, while
-- CAND_ID is still the one the list corrects: once FEC recodes the row itself, the correction no
-- longer applies. The handoff below then applies to the corrected candidate as to any other.
--
-- The race is the candidate's race in the seat calendar, or none. A candidate a spender targets
-- is not always one of the cycle: in 2024, 1,282 IE rows ($54,429,826, memo lines among them) name an id `cn` lacks or none, and others a candidate whose seat is not up (a
-- 2026 senator, a 2028 hopeful). Such a row is kept, its candidate or race null: the money is the
-- spender's ie_total all the same, and in no candidate's or race's figure.
--
-- A candidate a committee was handed from (`handoff`, fec/handoffs.csv, NEU-2126) is credited none
-- of the spending that names them on or after the handoff date: it is the candidate the committee
-- was handed to's, as the committee's own money is, and an undated row is theirs too (NEU-2277).
-- Committees kept filing Biden's id after he withdrew on 2024-07-21, close to $200M for him,
-- which is Harris's. The join is on the candidate ids, not the committee: an expenditure names
-- the candidate and no committee of theirs. Its side is kept as filed.
--
-- Each amount is kept as filed, a negative one included (a correction), so it nets out.
--
-- The 24/48-hour file (`ie_24_48`, 2010 on) is spenders' estimates, filed within a day or two,
-- which a periodic report later restates in `pas2`; it also holds hoax filings ($43.9B in 2024).
-- So it is no source of its own, and no row of it is matched to a `pas2` row. In order:
-- 1. The filing chain: a row on a filing another row's prev_file_num names is not read. Each
--    filing of a chain of amendments but the last is named by its successor.
-- 2. A row whose spender is no committee of the cycle is dropped, as a `pas2` row is.
-- 3. Timeliness: a row dated after its spender's `reported_total.period_end` is added when the
--    spender has a track record, a counted `pas2` independent expenditure (24A or 24E) or a
--    reported figure above $0. A spender with no period end has none added this way. The next
--    periodic report moves the end on, and the spending is `pas2`'s from that build.
-- 4. By spender, behind the hoax screen: a spender with no counted `pas2` independent
--    expenditure adds its remaining rows (on or before its period end, or undated) when it
--    reports independent expenditures above $0 and those rows add up to no more than ten times
--    that figure.
-- 5. Every other row is not read: `pas2` holds that spending already.
-- A row's date is exp_date, or dissem_dt where that is blank. Its key is `<file_num>:<tran_id>`,
-- unique in every cycle's file (silver_independent_expenditure_key.sql holds a build to it), so
-- `source_record_id` is text, and a `pas2` row's is its SUB_ID's digits. Its candidate follows
-- the alias and handoff rules below; the correction list is keyed by SUB_ID, so it applies to
-- `pas2` rows alone. Its side is sup_opp when that is S or O, else none: such a row is in its
-- spender's total and no candidate's. ie_24_48_added keeps which rule added each row, which the
-- transform logs (silver_independent_expenditure_no_double.sql checks the rules' outcome).
CREATE TEMP TABLE ie_24_48_added AS
WITH replaced AS (
    SELECT DISTINCT prev_file_num AS file_num FROM ie_24_48 WHERE prev_file_num IS NOT NULL
),
filed AS (
    SELECT
        ie.*,
        -- FEC writes DD-MON-YY; a malformed date is null rather than a failed build.
        coalesce(
            CAST(try_strptime(ie.exp_date, '%d-%b-%y') AS DATE),
            CAST(try_strptime(ie.dissem_dt, '%d-%b-%y') AS DATE)
        ) AS spent_on
    FROM ie_24_48 AS ie
    -- An anti-join, not NOT IN: a row with no file_num stays, for the key check to fail on.
    LEFT JOIN replaced ON replaced.file_num = ie.file_num
    WHERE replaced.file_num IS NULL
        AND ie.spe_id IN (SELECT committee_id FROM committee)
),
-- The spenders `pas2` holds a counted independent expenditure for: a 24A or 24E that is no memo
-- line, as `filed` below keeps them (each spender here is a committee of the cycle already).
pas2_spender AS (
    SELECT DISTINCT CMTE_ID AS committee_id
    FROM pas2
    WHERE TRANSACTION_TP IN ('24A', '24E')
        AND coalesce(MEMO_CD, '') <> 'X'
),
ruled AS (
    SELECT
        filed.*,
        reported.independent_expenditures AS reported_independent_expenditures,
        CASE
            WHEN filed.spent_on > reported.period_end
                AND (
                    pas2_spender.committee_id IS NOT NULL
                    OR reported.independent_expenditures > 0
                )
                THEN 'timeliness'
            WHEN pas2_spender.committee_id IS NULL AND reported.independent_expenditures > 0
                THEN 'by_spender'
        END AS rule
    FROM filed
    LEFT JOIN reported_total AS reported ON reported.committee_id = filed.spe_id
    LEFT JOIN pas2_spender ON pas2_spender.committee_id = filed.spe_id
),
screened AS (
    SELECT
        *,
        sum(exp_amo) FILTER (WHERE rule = 'by_spender') OVER (PARTITION BY spe_id)
            AS spender_rows
    FROM ruled
)
SELECT
    CAST(file_num AS VARCHAR) || ':' || tran_id AS source_record_id,
    spe_id AS committee_id,
    nullif(trim(cand_id), '') AS cand_id,
    CASE WHEN sup_opp IN ('S', 'O') THEN sup_opp END AS support_oppose,
    exp_amo AS amount,
    spent_on,
    pay AS payee_name,
    pur AS purpose,
    CAST(try_strptime(dissem_dt, '%d-%b-%y') AS DATE) AS dissemination_date,
    rule
FROM screened
WHERE rule = 'timeliness'
    OR (rule = 'by_spender' AND spender_rows <= 10 * reported_independent_expenditures);

CREATE TABLE independent_expenditure AS
WITH filed AS (
    SELECT
        CAST(pas2.SUB_ID AS VARCHAR) AS source_record_id,
        pas2.CMTE_ID AS committee_id,
        coalesce(corrected.candidate_id, nullif(trim(pas2.CAND_ID), '')) AS cand_id,
        CASE WHEN pas2.TRANSACTION_TP IN ('24A', '24N') THEN 'O' ELSE 'S' END AS support_oppose,
        pas2.TRANSACTION_AMT AS amount,
        -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
        CAST(try_strptime(pas2.TRANSACTION_DT, '%m%d%Y') AS DATE) AS spent_on,
        pas2.TRANSACTION_TP AS transaction_type,
        CASE pas2.TRANSACTION_TP
            WHEN '24C' THEN 'coordinated'
            WHEN '24F' THEN 'communication_cost'
            WHEN '24N' THEN 'communication_cost'
            ELSE 'ie'
        END AS kind,
        'pas2' AS source_file,
        pas2.NAME AS payee_name,
        CAST(NULL AS VARCHAR) AS purpose,
        CAST(NULL AS DATE) AS dissemination_date
    FROM pas2
    LEFT JOIN ie_candidate_correction AS corrected
        ON corrected.sub_id = pas2.SUB_ID
        AND corrected.pas2_candidate_id = trim(pas2.CAND_ID)
    WHERE pas2.TRANSACTION_TP IN ('24A', '24E', '24C', '24F', '24N')
        AND coalesce(pas2.MEMO_CD, '') <> 'X'
        AND pas2.CMTE_ID IN (SELECT committee_id FROM committee)
    UNION ALL
    SELECT
        source_record_id,
        committee_id,
        cand_id,
        support_oppose,
        amount,
        spent_on,
        CAST(NULL AS VARCHAR) AS transaction_type,
        'ie' AS kind,
        'ie_24_48' AS source_file,
        payee_name,
        purpose,
        dissemination_date
    FROM ie_24_48_added
),
spending AS (
    SELECT filed.*, coalesce(named.alias_of, named.candidate_id) AS named_candidate_id
    FROM filed
    LEFT JOIN candidate AS named ON named.candidate_id = filed.cand_id
),
handed_off AS (
    -- One row per pair of candidates and date, whichever committees were handed between them.
    SELECT DISTINCT from_candidate_id, to_candidate_id, handoff_date FROM handoff
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    spending.source_record_id,
    'US' AS jurisdiction,
    spending.committee_id,
    candidate.candidate_id,
    candidate.race_id,
    spending.support_oppose,
    spending.amount,
    spending.spent_on AS date,
    spending.transaction_type,
    spending.kind,
    spending.source_file,
    spending.payee_name,
    spending.purpose,
    spending.dissemination_date
FROM spending
LEFT JOIN handed_off
    ON handed_off.from_candidate_id = spending.named_candidate_id
    AND (spending.spent_on IS NULL OR spending.spent_on >= handed_off.handoff_date)
LEFT JOIN candidate
    ON candidate.candidate_id = coalesce(handed_off.to_candidate_id, spending.named_candidate_id);
