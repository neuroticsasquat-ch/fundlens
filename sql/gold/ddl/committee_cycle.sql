CREATE TABLE gold_build.committee_cycle (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    total_individual numeric(16, 2) NOT NULL,
    self_funding numeric(16, 2) NOT NULL,
    total_from_committees numeric(16, 2) NOT NULL,
    total_to_candidates numeric(16, 2) NOT NULL,
    ie_total numeric(16, 2) NOT NULL,
    PRIMARY KEY (committee_id, cycle)
);
