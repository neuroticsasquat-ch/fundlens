CREATE TABLE gold_build.race_top_donor (
    race_id text NOT NULL,
    rank integer NOT NULL,
    donor_id bigint NOT NULL,
    display_name text,
    amount numeric(16, 2) NOT NULL,
    candidates jsonb NOT NULL,
    PRIMARY KEY (race_id, rank)
);
