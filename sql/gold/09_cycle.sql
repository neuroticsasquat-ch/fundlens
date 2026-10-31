-- cycle (spec §7.1): the one row for the cycle being built. total_amount is every counted
-- contribution, self-funding included (expected.yaml's contributions.total_amount).
CREATE TABLE cycle AS
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    CAST((SELECT count(*) FROM race) AS INTEGER) AS race_count,
    CAST((SELECT count(*) FROM silver.contribution) AS BIGINT) AS contribution_count,
    CAST((SELECT coalesce(sum(amount), 0) FROM silver.contribution) AS DECIMAL(16, 2)) AS total_amount;
