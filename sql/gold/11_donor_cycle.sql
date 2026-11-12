-- donor_cycle (spec §7.1): every donor's counted money and contributions in each cycle they gave
-- in, self-funding included (it is the donor's money; it is kept off the top-donor lists, not off
-- the donor). A donor known only from JFC attributions in a cycle has a row of 0s for it.
CREATE TABLE donor_cycle AS
SELECT
    donor_id,
    CAST(cycle AS INTEGER) AS cycle,
    CAST(coalesce(sum(amount), 0) AS DECIMAL(16, 2)) AS amount,
    CAST(count(*) FILTER (WHERE counted) AS INTEGER) AS contribution_count
FROM donor_line
GROUP BY donor_id, cycle;
