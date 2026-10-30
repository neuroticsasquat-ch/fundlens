-- candidate_committee_link (spec §4): which committees `ccl` links to each candidate.
--
-- `ccl` can link one candidate and committee once per CAND_ELECTION_YR (a senator's committee
-- for this race and the next). The key is the pair, so the link kept is the one whose
-- CAND_ELECTION_YR is the cycle's where there is one, else the newest.
CREATE TABLE candidate_committee_link AS
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    CAND_ID AS candidate_id,
    CMTE_ID AS committee_id,
    'fec' AS source,
    'US' AS jurisdiction,
    CMTE_TP AS committee_type,
    CMTE_DSGN AS designation,
    LINKAGE_ID AS linkage_id
FROM ccl
QUALIFY row_number() OVER (
    PARTITION BY CAND_ID, CMTE_ID
    ORDER BY CAND_ELECTION_YR = {cycle} DESC, LINKAGE_ID DESC
) = 1;
