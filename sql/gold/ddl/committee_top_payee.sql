CREATE TABLE gold_build.committee_top_payee (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    rank integer NOT NULL,
    payee_key text NOT NULL,
    payee_id text,
    name text NOT NULL,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (committee_id, cycle, rank)
);
