-- No committee's total_refunds is above 0: it is the refunds counted in its total_individual and
-- total_from_organizations, each subtracting (NEU-2265). A positive figure means a refund was
-- counted with its filer's sign, or a receipt was taken for one.
SELECT committee_id, total_refunds
FROM committee_cycle
WHERE total_refunds > 0;
