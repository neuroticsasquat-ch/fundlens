-- Every receipt was recorded by a committee of the cycle: `oth` is filed by the recipient, so
-- its CMTE_ID must be in `cm`. (A giver, OTHER_ID, may be a committee the cycle's `cm` lacks.)
SELECT source_record_id, from_committee_id, to_committee_id, amount
FROM committee_transfer
WHERE side = 'receipt'
    AND NOT EXISTS (
        SELECT 1 FROM committee WHERE committee.committee_id = committee_transfer.to_committee_id
    );
