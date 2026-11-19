CREATE TABLE gold_build.candidate_gift_size (
    candidate_id text NOT NULL,
    cycle integer NOT NULL,
    bucket text NOT NULL,
    amount numeric(16, 2) NOT NULL,
    donors integer,
    PRIMARY KEY (candidate_id, cycle, bucket)
);
