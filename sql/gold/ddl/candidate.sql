CREATE TABLE gold_build.candidate (
    candidate_id text PRIMARY KEY,
    name text,
    party text,
    office text,
    state text,
    district text,
    cycles integer[] NOT NULL
);
