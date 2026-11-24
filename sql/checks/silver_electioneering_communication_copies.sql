-- No disbursement has more rows than the candidates it names (every-FEC-dollar spec §6.4,
-- NEU-2166): a disbursement is the rows equal on spender, image number, payee, date and amount, and
-- its rows beyond candidate_count are copies, which would count the ad's cost again. 2024's file
-- holds two such copies, $38,500.
SELECT committee_id, image_num, payee_name, date, disbursement_amount, count(*) AS row_count,
    max(candidate_count) AS candidate_count
FROM electioneering_communication
GROUP BY committee_id, image_num, payee_name, date, disbursement_amount
-- A disbursement with no count of 1 or more has no copies known, as the model keeps its rows.
HAVING max(candidate_count) >= 1 AND count(*) > max(candidate_count);
