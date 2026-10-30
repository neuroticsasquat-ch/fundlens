CREATE TABLE gold_build.race (
    race_id text PRIMARY KEY,
    cycle integer NOT NULL,
    office text NOT NULL,
    state text NOT NULL,
    district text NOT NULL,
    is_special boolean NOT NULL,
    slug text NOT NULL,
    candidate_count integer NOT NULL,
    total_individual numeric(16, 2) NOT NULL,
    total_committee numeric(16, 2) NOT NULL,
    ie_support numeric(16, 2) NOT NULL,
    ie_oppose numeric(16, 2) NOT NULL
);
