-- independent_expenditure (spec §4, NEU-2057): one row per `pas2` row that is a committee's spending
-- for or against a candidate rather than a gift to one. `pas2`'s 24Ks, committees' contributions
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
CREATE TABLE independent_expenditure AS
WITH spending AS (
    SELECT
        pas2.*,
        coalesce(named.alias_of, named.candidate_id) AS named_candidate_id,
        -- FEC writes MMDDYYYY; a malformed date is null rather than a failed build.
        CAST(try_strptime(pas2.TRANSACTION_DT, '%m%d%Y') AS DATE) AS spent_on
    FROM pas2
    LEFT JOIN ie_candidate_correction AS corrected
        ON corrected.sub_id = pas2.SUB_ID
        AND corrected.pas2_candidate_id = trim(pas2.CAND_ID)
    LEFT JOIN candidate AS named
        ON named.candidate_id = coalesce(corrected.candidate_id, nullif(trim(pas2.CAND_ID), ''))
    WHERE pas2.TRANSACTION_TP IN ('24A', '24E', '24C', '24F', '24N')
        AND coalesce(pas2.MEMO_CD, '') <> 'X'
        AND pas2.CMTE_ID IN (SELECT committee_id FROM committee)
),
handed_off AS (
    -- One row per pair of candidates and date, whichever committees were handed between them.
    SELECT DISTINCT from_candidate_id, to_candidate_id, handoff_date FROM handoff
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    'fec' AS source,
    spending.SUB_ID AS source_record_id,
    'US' AS jurisdiction,
    spending.CMTE_ID AS committee_id,
    candidate.candidate_id,
    candidate.race_id,
    CASE WHEN spending.TRANSACTION_TP IN ('24A', '24N') THEN 'O' ELSE 'S' END AS support_oppose,
    spending.TRANSACTION_AMT AS amount,
    spending.spent_on AS date,
    spending.TRANSACTION_TP AS transaction_type,
    CASE spending.TRANSACTION_TP
        WHEN '24C' THEN 'coordinated'
        WHEN '24F' THEN 'communication_cost'
        WHEN '24N' THEN 'communication_cost'
        ELSE 'ie'
    END AS kind
FROM spending
LEFT JOIN handed_off
    ON handed_off.from_candidate_id = spending.named_candidate_id
    AND (spending.spent_on IS NULL OR spending.spent_on >= handed_off.handoff_date)
LEFT JOIN candidate
    ON candidate.candidate_id = coalesce(handed_off.to_candidate_id, spending.named_candidate_id);
