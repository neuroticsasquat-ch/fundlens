CREATE TABLE gold_build.donor_cycle (
    donor_id bigint NOT NULL,
    cycle integer NOT NULL,
    amount numeric(16, 2) NOT NULL,
    contribution_count integer NOT NULL,
    PRIMARY KEY (donor_id, cycle)
);
