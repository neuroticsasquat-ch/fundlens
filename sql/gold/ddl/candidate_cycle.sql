CREATE TABLE gold_build.candidate_cycle (
    candidate_id text NOT NULL,
    cycle integer NOT NULL,
    race_id text,
    total_individual numeric(16, 2) NOT NULL,
    total_committee numeric(16, 2) NOT NULL,
    self_funding numeric(16, 2) NOT NULL,
    ie_support numeric(16, 2) NOT NULL,
    ie_oppose numeric(16, 2) NOT NULL,
    contributor_count integer,
    PRIMARY KEY (candidate_id, cycle)
);
