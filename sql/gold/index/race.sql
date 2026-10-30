-- The slug is the race page's URL; (cycle, office, state) is `GET /v1/cycles/{cycle}/races`.
CREATE UNIQUE INDEX race_slug ON gold_build.race (slug);
CREATE INDEX race_cycle_office_state ON gold_build.race (cycle, office, state);
