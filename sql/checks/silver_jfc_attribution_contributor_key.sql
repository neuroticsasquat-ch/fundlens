-- Every JFC attribution carries a contributor key with its row in the cycle's contributor: an
-- attribution reaches resolution only through one (spec §6.11).
SELECT source_record_id, contributor_name, contributor_key
FROM jfc_attribution
WHERE contributor_key IS NULL
    OR NOT EXISTS (
        SELECT 1 FROM contributor WHERE contributor.contributor_key = jfc_attribution.contributor_key
    );
