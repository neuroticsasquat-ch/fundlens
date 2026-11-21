CREATE TABLE gold_build.payee (
    payee_id text PRIMARY KEY,
    payee_key text NOT NULL UNIQUE,
    display_name text NOT NULL,
    city text,
    state text,
    total_all_cycles numeric(16, 2) NOT NULL,
    first_cycle integer NOT NULL,
    last_cycle integer NOT NULL
);
