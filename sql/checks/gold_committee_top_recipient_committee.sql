-- Every committee in a committee's top 100 recipients is a committee of the cycle, so it has a
-- page (NEU-2057), and a name unless `cm` lists it only as a skeleton row (06_committee.sql).
SELECT committee_id, rank, recipient_id
FROM committee_top_recipient
WHERE recipient_kind = 'committee'
    AND NOT EXISTS (SELECT 1 FROM committee WHERE committee.committee_id = committee_top_recipient.recipient_id);
