-- Every counted contribution went to a committee of the cycle (a silver check), so the
-- committees' receipts, own money included, add up to cycle.total_amount.
SELECT committees.total, cycle.total_amount
FROM (SELECT coalesce(sum(total_individual + self_funding), 0) AS total FROM committee_cycle) AS committees,
    cycle
WHERE committees.total <> cycle.total_amount;
