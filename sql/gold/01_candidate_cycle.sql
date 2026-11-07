-- candidate_cycle (spec §7.1, NEU-2039 §3): one row per silver candidate of the cycle, with or
-- without a race (the fixture's H4MD09109 has money but no seat), but an alias (NEU-2127): a
-- person's second id for the same race, holding no money, is in candidate_redirect instead. So
-- race_candidate, race.candidate_count and search_entity, all built from this, list each person
-- once.
--
-- total_individual is every counted contribution to a committee raising for the candidate that is
-- not the candidate's own money, nor on a line FEC's itemized figure leaves out (silver's
-- is_other_line, NEU-2193: a transfer, an earmark's conduit side, a loan); self_funding is that
-- own money (silver's is_self_funding), and neither includes the other. total_committee is the
-- committees' gifts to the candidate: the disbursement side of committee_transfer only (the
-- recipient's 18K twin would count each gift twice), less a giver whose 24Ks to the candidate net
-- below 0 for the cycle: returned gifts, voids of an earlier cycle's, in the giver's
-- total_returned_by_candidates and never the candidate's (NEU-2204).
-- total_jfc_transfers is the receipts of the committees raising for the candidate from a
-- joint fundraising committee (designation J): its transfers of the candidate's share (NEU-2124),
-- whatever receipt type the filer gave them (18G mostly, some 18J and 15J; FEC's own transfers-in
-- totals take them all). It is in neither figure above, and counts nothing twice: the JFC's own
-- contributions raise for no candidate.
-- Refunds are negative amounts and net out. Nothing to sum is 0, never NULL.
-- contributor_count is the donors whose counted gifts reached the candidate, their own money aside;
-- NULL for every candidate of a build loaded before `resolve`, whose contributions have no donor
-- (the loader gives them a NULL donor_id). ie_support and ie_oppose are 0 until NEU-2057.
CREATE TABLE candidate_cycle AS
WITH money AS (
    SELECT
        candidate_id,
        coalesce(sum(amount) FILTER (WHERE NOT is_self_funding AND NOT is_other_line), 0)
            AS total_individual,
        coalesce(sum(amount) FILTER (WHERE is_self_funding), 0) AS self_funding,
        count(DISTINCT donor_id) FILTER (WHERE NOT is_self_funding AND NOT is_other_line)
            AS contributor_count
    FROM silver.contribution
    WHERE candidate_id IS NOT NULL
    GROUP BY candidate_id
),
resolved AS (
    SELECT count(donor_id) = count(*) AS resolved FROM silver.contribution
),
from_committees AS (
    SELECT candidate_id, sum(amount) AS total_committee
    FROM (
        SELECT from_committee_id, candidate_id, sum(amount) AS amount
        FROM silver.committee_transfer
        WHERE side = 'disbursement' AND candidate_id IS NOT NULL
        GROUP BY from_committee_id, candidate_id
        HAVING sum(amount) >= 0
    ) AS given
    GROUP BY candidate_id
),
jfc_transfers AS (
    SELECT transfer.candidate_id, sum(transfer.amount) AS total_jfc_transfers
    FROM silver.committee_transfer AS transfer
    JOIN silver.committee AS jfc
        ON jfc.committee_id = transfer.from_committee_id AND jfc.designation = 'J'
    WHERE transfer.side = 'receipt' AND transfer.candidate_id IS NOT NULL
    GROUP BY transfer.candidate_id
)
SELECT
    candidate.candidate_id,
    CAST({cycle} AS INTEGER) AS cycle,
    candidate.race_id,
    CAST(coalesce(money.total_individual, 0) AS DECIMAL(16, 2)) AS total_individual,
    CAST(coalesce(from_committees.total_committee, 0) AS DECIMAL(16, 2)) AS total_committee,
    CAST(coalesce(jfc_transfers.total_jfc_transfers, 0) AS DECIMAL(16, 2)) AS total_jfc_transfers,
    CAST(coalesce(money.self_funding, 0) AS DECIMAL(16, 2)) AS self_funding,
    CAST(0 AS DECIMAL(16, 2)) AS ie_support,
    CAST(0 AS DECIMAL(16, 2)) AS ie_oppose,
    CASE
        WHEN resolved.resolved THEN CAST(coalesce(money.contributor_count, 0) AS INTEGER)
    END AS contributor_count
FROM silver.candidate AS candidate
CROSS JOIN resolved
LEFT JOIN money USING (candidate_id)
LEFT JOIN from_committees USING (candidate_id)
LEFT JOIN jfc_transfers USING (candidate_id)
WHERE candidate.alias_of IS NULL;
