-- One handoff per committee (fec/handoffs.csv): a second would link the committee twice over the
-- same dates and count each of its rows twice (NEU-2126).
SELECT committee_id, count(*) AS copies
FROM handoff
GROUP BY committee_id
HAVING count(*) > 1;
