-- Every search row has a name to match on, and (kind, id) is its key.
SELECT kind, id, count(*) AS rows
FROM search_entity
GROUP BY kind, id
HAVING count(*) > 1 OR bool_or(name IS NULL);
