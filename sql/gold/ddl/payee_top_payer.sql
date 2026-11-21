CREATE TABLE gold_build.payee_top_payer (
    payee_id text NOT NULL,
    cycle integer NOT NULL,
    rank integer NOT NULL,
    committee_id text NOT NULL,
    candidate_id text,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (payee_id, cycle, rank)
);
