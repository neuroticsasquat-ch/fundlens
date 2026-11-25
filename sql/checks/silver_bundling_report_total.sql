-- Per committee and half-year, bundling_report's amount sums to the bundled total
-- (every-FEC-dollar spec §7.6, NEU-2175): the greater of the half-year figure and the innermost
-- kept reports' period amounts, worked out here again from the FEC's file, so a report placed
-- wrong, or a half the model left out, fails the build. The rules are §7.5's and §7.6's, spelled
-- as 16_bundling_report.sql spells them: kept is the latest receipt date, then the higher image
-- number, per committee and covered period, a report missing a coverage date always kept; the
-- half-year figure is the semi-annual amount above $0 of the kept report with the latest coverage
-- end, then the later start, then the higher image number; innermost are the kept reports whose
-- covered period holds no other kept report of the committee.
WITH filed AS (
    SELECT
        trim(Committee_Id) AS committee_id,
        TRY_CAST(regexp_extract(Link_Image, '[?]_?([0-9]+)', 1) AS HUGEINT) AS image,
        CAST(try_strptime(Receipt_Date, '%d-%b-%y') AS DATE) AS received,
        CAST(try_strptime(Coverage_Start_Date, '%d-%b-%y') AS DATE) AS covers_from,
        CAST(try_strptime(Coverage_End_Date, '%d-%b-%y') AS DATE) AS covers_to,
        Quarterly_Contribution AS period_amount,
        Semi_Annual_Contribution AS semi_annual_amount
    FROM lobbyist_bundle
),
kept AS (
    SELECT
        *,
        CAST(year(covers_to) AS VARCHAR) || '-'
            || CASE WHEN month(covers_to) <= 6 THEN '1' ELSE '2' END AS half_year
    FROM filed
    WHERE covers_to IS NOT NULL
        AND year(covers_to) + year(covers_to) % 2 = {cycle}
        AND committee_id IN (SELECT committee_id FROM committee)
    QUALIFY covers_from IS NULL
        OR row_number() OVER (
            PARTITION BY committee_id, covers_from, covers_to
            ORDER BY received DESC NULLS LAST, image DESC NULLS LAST
        ) = 1
),
-- Every kept report of the file, any cycle's: one spanning two cycles holds the reports in it.
every_kept AS (
    SELECT committee_id, covers_from, covers_to
    FROM filed
    WHERE covers_to IS NOT NULL
    QUALIFY covers_from IS NULL
        OR row_number() OVER (
            PARTITION BY committee_id, covers_from, covers_to
            ORDER BY received DESC NULLS LAST, image DESC NULLS LAST
        ) = 1
),
innermost AS (
    SELECT committee_id, half_year, sum(coalesce(period_amount, 0)) AS amount
    FROM kept
    WHERE NOT EXISTS (
        SELECT 1
        FROM every_kept AS other
        WHERE other.committee_id = kept.committee_id
            AND other.covers_from >= kept.covers_from
            AND other.covers_to <= kept.covers_to
            AND (other.covers_from <> kept.covers_from OR other.covers_to <> kept.covers_to)
    )
    GROUP BY committee_id, half_year
),
half_year_figure AS (
    SELECT committee_id, half_year, semi_annual_amount AS amount
    FROM kept
    WHERE semi_annual_amount > 0
    QUALIFY row_number() OVER (
        PARTITION BY committee_id, half_year
        ORDER BY covers_to DESC, covers_from DESC NULLS LAST, image DESC NULLS LAST
    ) = 1
),
expected AS (
    SELECT
        committee_id,
        half_year,
        greatest(coalesce(half_year_figure.amount, 0), coalesce(innermost.amount, 0)) AS amount
    FROM (SELECT DISTINCT committee_id, half_year FROM kept) AS halves
    LEFT JOIN innermost USING (committee_id, half_year)
    LEFT JOIN half_year_figure USING (committee_id, half_year)
),
placed AS (
    SELECT committee_id, half_year, sum(amount) AS amount
    FROM bundling_report
    WHERE half_year IS NOT NULL
    GROUP BY committee_id, half_year
)
SELECT
    coalesce(placed.committee_id, expected.committee_id) AS committee_id,
    coalesce(placed.half_year, expected.half_year) AS half_year,
    placed.amount AS placed,
    expected.amount AS expected
FROM placed
FULL JOIN expected USING (committee_id, half_year)
WHERE coalesce(placed.amount, 0) <> coalesce(expected.amount, 0);
