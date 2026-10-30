CREATE TABLE gold_build.committee (
    committee_id text PRIMARY KEY,
    name text,
    type text,
    designation text,
    party text,
    connected_org text,
    is_conduit boolean NOT NULL,
    cycles integer[] NOT NULL
);
