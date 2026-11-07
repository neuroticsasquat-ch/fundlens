CREATE TABLE gold_build.donor (
    donor_id bigint PRIMARY KEY,
    display_name text,
    employer text,
    occupation text,
    city text,
    state text,
    zip5 text,
    total_all_cycles numeric(16, 2) NOT NULL,
    first_cycle integer NOT NULL,
    last_cycle integer NOT NULL,
    contributor_key_count integer NOT NULL
);
