CREATE TABLE gold_build.reconciliation (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    measure text NOT NULL,
    fundlens numeric(16, 2) NOT NULL,
    reported numeric(16, 2) NOT NULL,
    ratio double precision,
    PRIMARY KEY (committee_id, cycle, measure)
);
