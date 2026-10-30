CREATE TABLE gold_build.race_top_committee (
    race_id text NOT NULL,
    rank integer NOT NULL,
    committee_id text NOT NULL,
    name text,
    amount numeric(16, 2) NOT NULL,
    kind text NOT NULL,
    PRIMARY KEY (race_id, rank)
);
