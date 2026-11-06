-- A row is marked non-contribution-account money exactly when it is a type 10, 10J or 20Y to or
-- from a hybrid PAC (committee type V or W), or a 24I there whose memo begins
-- "* NON-CONTRIBUTION ACCOUNT", in contribution and in organization_receipt alike (NEU-2192,
-- NEU-2203, NEU-2207): an unmarked one would put the account's money back in total_individual or
-- total_from_organizations, a marked 22Y, or a 24I without that memo, take contribution-account
-- money out of it.
WITH marking AS (
    SELECT 'contribution' AS in_table, source_record_id, transaction_type,
        recipient_committee_id, memo_text, is_non_contribution_account
    FROM contribution
    UNION ALL
    SELECT 'organization_receipt', source_record_id, transaction_type, recipient_committee_id,
        memo_text, is_non_contribution_account
    FROM organization_receipt
)
SELECT marking.in_table, marking.source_record_id, marking.transaction_type, committee.type,
    marking.is_non_contribution_account
FROM marking
LEFT JOIN committee ON committee.committee_id = marking.recipient_committee_id
WHERE marking.is_non_contribution_account IS DISTINCT FROM coalesce(
    committee.type IN ('V', 'W') AND (
        marking.transaction_type IN ('10', '10J', '20Y')
        OR marking.transaction_type = '24I'
            AND starts_with(upper(marking.memo_text), '* NON-CONTRIBUTION ACCOUNT')
    ),
    false
);
