-- A superseded report, or one with no coverage end, adds nothing to the bundled total
-- (every-FEC-dollar spec §7.5, NEU-2175): an amendment restates the report it supersedes, so both
-- would count it twice, and a report with no coverage end falls in no half-year.
SELECT source_record_id, committee_id, is_superseded, coverage_end, amount
FROM bundling_report
WHERE (is_superseded OR coverage_end IS NULL) AND amount <> 0;
