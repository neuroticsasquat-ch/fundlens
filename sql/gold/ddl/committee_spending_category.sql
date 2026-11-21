CREATE TABLE gold_build.committee_spending_category (
    committee_id text NOT NULL,
    cycle integer NOT NULL,
    category text NOT NULL,
    amount numeric(16, 2) NOT NULL,
    PRIMARY KEY (committee_id, cycle, category)
);
