CREATE TABLE gold_build.race_top_spender (
    race_id text NOT NULL,
    rank integer NOT NULL,
    committee_id text NOT NULL,
    name text,
    candidate_id text NOT NULL,
    kind text NOT NULL,
    support_oppose text,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (race_id, rank)
);
