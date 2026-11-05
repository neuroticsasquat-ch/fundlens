CREATE TABLE gold_build.committee_top_organization (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    rank integer NOT NULL,
    organization_key text NOT NULL,
    name text NOT NULL,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (committee_id, cycle, rank)
);
