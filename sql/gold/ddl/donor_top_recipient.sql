CREATE TABLE gold_build.donor_top_recipient (
    donor_id bigint NOT NULL,
    rank integer NOT NULL,
    recipient_kind text NOT NULL,
    recipient_id text NOT NULL,
    name text,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (donor_id, rank)
);
