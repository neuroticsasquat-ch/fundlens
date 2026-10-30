-- committee (spec §4): one row per `cm` committee in the cycle.
-- A conduit (ActBlue, WinRed; CONTEXT.md) is flagged from the vendored list, never inferred.
CREATE TABLE committee AS
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    CMTE_ID AS committee_id,
    'fec' AS source,
    'US' AS jurisdiction,
    CMTE_NM AS name,
    TRES_NM AS treasurer,
    -- concat_ws skips nulls but gives '' when both lines are blank.
    nullif(concat_ws(' ', CMTE_ST1, CMTE_ST2), '') AS street,
    CMTE_CITY AS city,
    CMTE_ST AS state,
    CMTE_ZIP AS zip,
    CMTE_DSGN AS designation,
    CMTE_TP AS type,
    CMTE_PTY_AFFILIATION AS party,
    CMTE_FILING_FREQ AS filing_frequency,
    ORG_TP AS org_type,
    CONNECTED_ORG_NM AS connected_org,
    CAND_ID AS candidate_id,
    CMTE_ID IN (SELECT committee_id FROM conduit) AS is_conduit
FROM cm;
