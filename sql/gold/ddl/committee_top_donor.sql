CREATE TABLE gold_build.committee_top_donor (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    rank integer NOT NULL,
    donor_id bigint NOT NULL,
    display_name text,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (committee_id, cycle, rank)
);
