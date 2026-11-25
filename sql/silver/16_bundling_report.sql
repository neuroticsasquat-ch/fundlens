-- bundling_report (every-FEC-dollar spec §7.5, §7.6, NEU-2175): one row per Form 3L report in
-- `lobbyist_bundle.csv` whose recipient is a committee of its cycle, amendments included: a
-- report of the contributions registered lobbyists and lobbyist PACs bundled to a campaign, party
-- committee or leadership PAC. The bundled gifts are already the individuals' contributions in
-- `contribution`, so a bundled total is context, never added to a receipt total. The file names
-- no bundler and no donor.
--
-- The file is undated, one for every cycle from 2010 (before it the runner gives an empty one). A
-- report's cycle is its coverage end's year, rounded up to even; with no coverage end, its receipt
-- date's. Its half_year (`<yyyy>-1` January-June, `<yyyy>-2` July-December) is its coverage end's.
--
-- Amendments (§7.5, Decision 7): among a committee's reports with the same coverage start and end,
-- the one with the latest Receipt_Date, then the higher image number, is kept; the rest are
-- superseded and add 0. A report missing either coverage date is never superseded.
--
-- amount, what a report adds to the bundled total (§7.6, Decision 8), is placed so that per
-- committee and half-year it sums to the greater of
--   - the half-year figure: the semi-annual amount on the kept report with the latest coverage end
--     in the half carrying one above $0; between two with the same end, the later coverage start,
--     then the higher image number;
--   - the innermost period amounts: the period amounts of the kept reports whose covered period
--     holds no other kept report of the committee (a six-month report beside its quarters holds
--     them, and adds nothing of its own: Form 3L asks for both figures, which never add).
-- So a kept report adds its period amount unless it holds another kept report of its committee;
-- the report carrying the half-year figure also adds what that figure exceeds the half's innermost
-- period amounts by; every other row adds 0. A report with no coverage start holds no other report
-- and is held by none; one with no coverage end falls in no half and adds 0. Kept-ness, holding
-- and the half-year figure are read over the whole file, so a report spanning two cycles still
-- holds the reports inside it.
--
-- A report whose recipient is no committee of its cycle is dropped (§7.5): five $0 reports under
-- hoax-like names across 2010-2026. source_record_id is the report's image number, the digits
-- after `?_` (or `?`) in Link_Image: unique in the file.
CREATE TABLE bundling_report AS
WITH parsed AS (
    SELECT
        nullif(regexp_extract(Link_Image, '[?]_?([0-9]+)', 1), '') AS source_record_id,
        trim(Committee_Id) AS committee_id,
        Report_Type AS report_type,
        -- FEC writes DD-MON-YY; a malformed date is null rather than a failed build.
        CAST(try_strptime(Receipt_Date, '%d-%b-%y') AS DATE) AS receipt_date,
        CAST(try_strptime(Coverage_Start_Date, '%d-%b-%y') AS DATE) AS coverage_start,
        CAST(try_strptime(Coverage_End_Date, '%d-%b-%y') AS DATE) AS coverage_end,
        Quarterly_Contribution AS period_amount,
        Semi_Annual_Contribution AS semi_annual_amount
    FROM lobbyist_bundle
),
ranked AS (
    SELECT
        *,
        TRY_CAST(source_record_id AS HUGEINT) AS image_order,
        coalesce(
            coverage_start IS NOT NULL
            AND coverage_end IS NOT NULL
            AND row_number() OVER (
                PARTITION BY committee_id, coverage_start, coverage_end
                ORDER BY receipt_date DESC NULLS LAST, TRY_CAST(source_record_id AS HUGEINT) DESC NULLS LAST
            ) > 1,
            false
        ) AS is_superseded
    FROM parsed
),
held AS (
    SELECT
        ranked.*,
        NOT ranked.is_superseded AND ranked.coverage_end IS NOT NULL AS places,
        EXISTS (
            SELECT 1
            FROM ranked AS inner_report
            WHERE inner_report.committee_id = ranked.committee_id
                AND NOT inner_report.is_superseded
                AND inner_report.coverage_start >= ranked.coverage_start
                AND inner_report.coverage_end <= ranked.coverage_end
                AND (
                    inner_report.coverage_start <> ranked.coverage_start
                    OR inner_report.coverage_end <> ranked.coverage_end
                )
        ) AS holds_another,
        CAST(year(ranked.coverage_end) AS VARCHAR) || '-'
            || CASE WHEN month(ranked.coverage_end) <= 6 THEN '1' ELSE '2' END AS half_year,
        year(coalesce(ranked.coverage_end, ranked.receipt_date)) AS report_year
    FROM ranked
),
placed AS (
    SELECT
        *,
        CASE WHEN places AND NOT holds_another THEN coalesce(period_amount, 0) ELSE 0 END
            AS own_amount,
        coalesce(places AND semi_annual_amount > 0, false) AS may_carry
    FROM held
),
halves AS (
    SELECT
        *,
        sum(own_amount) OVER (PARTITION BY committee_id, half_year) AS innermost,
        may_carry AND row_number() OVER (
            PARTITION BY committee_id, half_year, may_carry
            ORDER BY coverage_end DESC, coverage_start DESC NULLS LAST, image_order DESC NULLS LAST
        ) = 1 AS carries_half_year_figure
    FROM placed
)
SELECT
    CAST(report_year + report_year % 2 AS INTEGER) AS cycle,
    'fec' AS source,
    source_record_id,
    'US' AS jurisdiction,
    committee_id,
    report_type,
    receipt_date,
    coverage_start,
    coverage_end,
    half_year,
    period_amount,
    semi_annual_amount,
    is_superseded,
    CAST(
        own_amount
        + CASE
            WHEN carries_half_year_figure THEN greatest(semi_annual_amount - innermost, 0)
            ELSE 0
        END
        AS DECIMAL(14, 2)
    ) AS amount
FROM halves
WHERE report_year + report_year % 2 = {cycle}
    AND committee_id IN (SELECT committee_id FROM committee);
