-- A row is marked non-contribution-account money exactly when it is a type 10 or 10J to a hybrid
-- PAC (committee type V or W), or a refund (2nY, 4nY) at one to a giver it holds such a row from
-- by the same name, in contribution and in organization_receipt alike (NEU-2192): an unmarked one
-- would put the account's money back in total_individual or total_from_organizations.
WITH contribution_rule AS (
    SELECT
        contribution.source_record_id,
        contribution.transaction_type,
        committee.type,
        contribution.is_non_contribution_account,
        coalesce(committee.type IN ('V', 'W') AND (
            contribution.transaction_type IN ('10', '10J')
            OR (
                regexp_matches(contribution.transaction_type, '^[24][0-9]Y$')
                AND EXISTS (
                    SELECT 1
                    FROM contribution AS gift
                    WHERE gift.recipient_committee_id = contribution.recipient_committee_id
                        AND gift.contributor_name = contribution.contributor_name
                        AND gift.transaction_type IN ('10', '10J')
                )
            )
        ), false) AS expected
    FROM contribution
    LEFT JOIN committee ON committee.committee_id = contribution.recipient_committee_id
),
organization_rule AS (
    SELECT
        receipt.source_record_id,
        receipt.transaction_type,
        committee.type,
        receipt.is_non_contribution_account,
        coalesce(committee.type IN ('V', 'W') AND (
            receipt.transaction_type IN ('10', '10J')
            OR (
                regexp_matches(receipt.transaction_type, '^[24][0-9]Y$')
                AND EXISTS (
                    SELECT 1
                    FROM organization_receipt AS gift
                    WHERE gift.recipient_committee_id = receipt.recipient_committee_id
                        AND gift.organization_name = receipt.organization_name
                        AND gift.transaction_type IN ('10', '10J')
                )
            )
        ), false) AS expected
    FROM organization_receipt AS receipt
    LEFT JOIN committee ON committee.committee_id = receipt.recipient_committee_id
)
SELECT 'contribution' AS in_table, source_record_id, transaction_type, type,
    is_non_contribution_account
FROM contribution_rule
WHERE is_non_contribution_account IS DISTINCT FROM expected
UNION ALL
SELECT 'organization_receipt', source_record_id, transaction_type, type,
    is_non_contribution_account
FROM organization_rule
WHERE is_non_contribution_account IS DISTINCT FROM expected;
