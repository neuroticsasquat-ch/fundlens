CREATE TABLE gold_build.cycle (
    cycle integer PRIMARY KEY,
    race_count integer NOT NULL,
    contribution_count bigint NOT NULL,
    total_amount numeric(16, 2) NOT NULL
);
