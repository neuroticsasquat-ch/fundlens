-- A receipt the name-match rule found (NEU-2131: an `indiv` row typed PAC, COM, CCM or PTY, or
-- an `oth` row with a blank OTHER_ID, naming one `cm` committee) has no twin: `oth` holds no
-- receipt of the same gift under the giver's id (same recipient, giver, amount and date). Were
-- there one, the gift would be counted twice. Such a receipt is one whose own `oth` row does not
-- carry its giver's id and whose giver is no JFC: a JFC named by NAME is NEU-2124's rule, which
-- has no twin rule. The bulk file on the left, so the join builds on the transfers.
SELECT
    receipt.source_record_id,
    receipt.from_committee_id,
    receipt.to_committee_id,
    receipt.amount,
    twin.SUB_ID AS twin_record_id
FROM oth AS twin
JOIN committee_transfer AS receipt
    ON twin.CMTE_ID = receipt.to_committee_id
    AND trim(twin.OTHER_ID) = receipt.from_committee_id
    AND twin.TRANSACTION_AMT = receipt.amount
    AND CAST(try_strptime(twin.TRANSACTION_DT, '%m%d%Y') AS DATE) = receipt.date
    AND twin.SUB_ID <> receipt.source_record_id
WHERE receipt.side = 'receipt'
    AND left(twin.TRANSACTION_TP, 1) IN ('1', '3')
    AND twin.MEMO_CD IS DISTINCT FROM 'X'
    AND NOT EXISTS (
        SELECT 1 FROM oth AS own
        WHERE own.SUB_ID = receipt.source_record_id
            AND trim(own.OTHER_ID) = receipt.from_committee_id
    )
    AND NOT EXISTS (
        SELECT 1 FROM committee
        WHERE committee.committee_id = receipt.from_committee_id AND committee.designation = 'J'
    );
