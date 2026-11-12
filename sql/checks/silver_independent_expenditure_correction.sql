-- Every correction that applies this cycle (fec/ie_candidate_corrections.csv, NEU-2279: its row is
-- in `pas2`, still coded as the list says) names a candidate of the cycle. One that names an id
-- `cn` lacks would leave its row attached to no candidate, its money in no candidate's figure,
-- where the correction meant to move it. A row FEC has recoded since is no correction's.
SELECT pas2.SUB_ID, correction.candidate_id
FROM pas2
JOIN ie_candidate_correction AS correction
    ON correction.sub_id = pas2.SUB_ID
    AND correction.pas2_candidate_id = trim(pas2.CAND_ID)
LEFT JOIN candidate ON candidate.candidate_id = correction.candidate_id
WHERE candidate.candidate_id IS NULL;
