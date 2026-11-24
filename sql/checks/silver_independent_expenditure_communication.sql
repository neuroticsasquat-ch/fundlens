-- A communication's type and class are set only on a communication cost (every-FEC-dollar spec
-- §6.2, NEU-2167): `CommunicationCosts` describes `pas2`'s 24F and 24N rows, joined by SUB_ID, and
-- no other row. One set elsewhere is a CSV row joined onto another kind's `pas2` row.
SELECT source_record_id, kind, communication_type, communication_class
FROM independent_expenditure
WHERE (communication_type IS NOT NULL OR communication_class IS NOT NULL)
    AND kind IS DISTINCT FROM 'communication_cost';
