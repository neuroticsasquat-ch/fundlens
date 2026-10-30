CREATE TABLE gold_build.committee_top_recipient (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    rank integer NOT NULL,
    recipient_kind text NOT NULL,
    recipient_id text NOT NULL,
    name text,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (committee_id, cycle, rank)
);
