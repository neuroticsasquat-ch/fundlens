CREATE TABLE gold_build.race_candidate (
    race_id text NOT NULL,
    candidate_id text NOT NULL,
    name text,
    party text,
    incumbent_challenger_open text,
    principal_committee_id text,
    total_individual numeric(16, 2) NOT NULL,
    total_committee numeric(16, 2) NOT NULL,
    self_funding numeric(16, 2) NOT NULL,
    ie_support numeric(16, 2) NOT NULL,
    ie_oppose numeric(16, 2) NOT NULL,
    PRIMARY KEY (race_id, candidate_id)
);
