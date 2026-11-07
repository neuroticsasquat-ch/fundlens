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

-- candidate.alias_of (NEU-2127): FEC sometimes registers one person under two candidate ids for
-- the same seat and cycle, an old id from an earlier run beside a new one, both linked to the same
-- committee (Hovde's 2024 S2WI00268 and S4WI00256). The committee's money is credited to one of
-- them, and the other would stand in the race beside them with nothing. That other is an alias of
-- the one credited, when the two:
-- - are candidates of the same race,
-- - are both linked principal (P) or authorized (A) to a committee credited to the one, and
-- - share a last name and first given name, compared as 04_contribution.sql's self-funding test
--   compares them ('HOVDE, ERIC D' is 'HOVDE, ERIC').
-- A committee is credited by the `linked` rule of 04_contribution.sql (and 06_jfc_attribution.sql),
-- and by 05_committee_transfer.sql's, which passes over an id `cn` lacks: where `ccl` links the
-- committee to one, the two can credit different candidates, and each counts. An alias is credited
-- no committee by either rule, and is in no handoff, so it holds no money of its own and none
-- moves: the person's id is the one already holding it. The one it names is credited a
-- committee, so is never an alias itself. Should two qualify, the lower candidate_id is named.
UPDATE candidate
SET alias_of = alias.canonical_id
FROM (
    WITH eligible AS (
        -- Both `linked` rules, a handoff's dated links aside: each link that may credit its
        -- committee, ranked principal first, then by candidate_id; `in_cn`, whether 05's rule
        -- sees it.
        SELECT
            link.committee_id,
            link.candidate_id,
            candidate.candidate_id IS NOT NULL AS in_cn,
            (link.designation = 'P' OR link.committee_id = candidate.principal_committee_id)
                AS is_principal
        FROM candidate_committee_link AS link
        LEFT JOIN candidate USING (candidate_id)
        WHERE (link.designation IN ('P', 'A') OR link.committee_id = candidate.principal_committee_id)
            AND link.committee_id NOT IN (SELECT committee_id FROM handoff)
    ),
    credited AS (
        SELECT committee_id, candidate_id
        FROM eligible
        QUALIFY row_number() OVER (
            PARTITION BY committee_id ORDER BY is_principal DESC, candidate_id
        ) = 1
        UNION
        SELECT committee_id, candidate_id
        FROM eligible
        WHERE in_cn
        QUALIFY row_number() OVER (
            PARTITION BY committee_id ORDER BY is_principal DESC, candidate_id
        ) = 1
    ),
    named AS (
        SELECT
            candidate_id,
            race_id,
            regexp_replace(upper(split_part(name, ',', 1)), '[^A-Z0-9]', '', 'g') AS last_name,
            regexp_replace(
                upper(split_part(trim(split_part(name, ',', 2)), ' ', 1)), '[^A-Z0-9]', '', 'g'
            ) AS first_name
        FROM candidate
        WHERE race_id IS NOT NULL
    ),
    linked_pa AS (
        SELECT committee_id, candidate_id
        FROM candidate_committee_link
        WHERE designation IN ('P', 'A')
    )
    SELECT alias.candidate_id, min(canonical.candidate_id) AS canonical_id
    FROM linked_pa AS alias_link
    JOIN credited
        ON credited.committee_id = alias_link.committee_id
        AND credited.candidate_id <> alias_link.candidate_id
    JOIN linked_pa AS canonical_link
        ON canonical_link.committee_id = credited.committee_id
        AND canonical_link.candidate_id = credited.candidate_id
    JOIN named AS alias ON alias.candidate_id = alias_link.candidate_id
    JOIN named AS canonical ON canonical.candidate_id = credited.candidate_id
    WHERE alias.race_id = canonical.race_id
        AND alias.last_name = canonical.last_name
        AND alias.first_name = canonical.first_name
        AND alias.candidate_id NOT IN (SELECT candidate_id FROM credited)
        AND alias.candidate_id NOT IN (
            SELECT from_candidate_id FROM handoff UNION ALL SELECT to_candidate_id FROM handoff
        )
    GROUP BY alias.candidate_id
) AS alias
WHERE candidate.candidate_id = alias.candidate_id;
