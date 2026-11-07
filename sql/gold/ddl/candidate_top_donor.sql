CREATE TABLE gold_build.candidate_top_donor (
    candidate_id text NOT NULL,
    cycle integer NOT NULL,
    rank integer NOT NULL,
    donor_id bigint NOT NULL,
    display_name text,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (candidate_id, cycle, rank)
);
