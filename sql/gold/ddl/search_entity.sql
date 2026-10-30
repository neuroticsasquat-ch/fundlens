CREATE TABLE gold_build.search_entity (
    kind text NOT NULL,
    id text NOT NULL,
    name text NOT NULL,
    aliases text,
    weight numeric(16, 2) NOT NULL,
    PRIMARY KEY (kind, id)
);
