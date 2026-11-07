-- Every JFC attribution's participant, and its JFC when one is known, is a committee of the cycle:
-- the participant filed the line, and the JFC is found among the cycle's committees.
SELECT source_record_id, participant_committee_id, jfc_committee_id
FROM jfc_attribution
WHERE NOT EXISTS (
        SELECT 1 FROM committee
        WHERE committee.committee_id = jfc_attribution.participant_committee_id
    )
    OR (
        jfc_committee_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM committee WHERE committee.committee_id = jfc_attribution.jfc_committee_id
        )
    );
