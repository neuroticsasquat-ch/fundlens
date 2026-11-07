-- An organization receipt is `classified` exactly when it was filed with no entity type: the
-- classifier is the only way a blank-type row gets here, and it never reads a filled type
-- (NEU-2132).
SELECT source_record_id, entity_type, classified
FROM organization_receipt
WHERE classified IS DISTINCT FROM (nullif(trim(entity_type), '') IS NULL);
