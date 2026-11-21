CREATE TABLE gold_build.payee_cycle (
    payee_id text NOT NULL,
    cycle integer NOT NULL,
    total numeric(16, 2) NOT NULL,
    committee_count integer NOT NULL,
    PRIMARY KEY (payee_id, cycle)
);
