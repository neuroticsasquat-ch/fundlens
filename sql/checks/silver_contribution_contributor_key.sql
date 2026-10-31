-- Every contribution carries a contributor key (spec §6.1): resolution reaches a contribution only
-- through one. Every counted contribution is an individual's or a candidate's (IND, CAN or blank).
-- 04_contribution.sql builds the key so that it is never null, an unreported value contributing an
-- empty part; this holds any later rewrite of it to the same.
SELECT source_record_id, entity_type, contributor_name
FROM contribution
WHERE contributor_key IS NULL;
