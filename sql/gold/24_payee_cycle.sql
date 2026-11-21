-- payee_cycle (every-FEC-dollar spec §5.5): a payee's payee dollars in each cycle it was paid in,
-- net as filed, and how many committees paid it. One row per payee with a page (payee_page,
-- 22_payee.sql) and cycle with a payee row; a cycle netting to $0 or less is kept, so the rows add
-- up to payee.total_all_cycles. committee_count counts every committee with a payee row for the
-- key in the cycle, one whose rows net to $0 or less too, which payee_top_payer leaves out.
CREATE TABLE payee_cycle AS
SELECT
    payee_page.payee_id,
    CAST(payee_row.cycle AS INTEGER) AS cycle,
    CAST(sum(payee_row.amount) AS DECIMAL(16, 2)) AS total,
    CAST(count(DISTINCT payee_row.committee_id) AS INTEGER) AS committee_count
FROM payee_row
JOIN payee_page USING (payee_key)
GROUP BY payee_page.payee_id, payee_row.cycle;
