-- lobbyist_pac (every-FEC-dollar spec §7.2, §7.3, NEU-2175): one row per committee of the cycle
-- that `lobbyist.csv` flags as a lobbyist/registrant PAC: a PAC run by a registered lobbyist or
-- a lobbying registrant, a fact about who runs it, told apart from the designation (`cm`'s B) a
-- page already shows.
--
-- Rule b (§7.2, Decision 6): a committee is flagged when its latest Form 1 filed on or before the
-- cycle's last day has the lobbyist/registrant box ticked (Is_Lobbyist `Y`): the latest
-- Date_Filed, then the higher image number in Link_Image (two committees filed Form 1s of one day
-- that disagree, and in both the higher number is ticked). A blank box is unticked. A Form 1
-- filed after the cycle is not read for it, so a committee that unticks the box later is still
-- flagged in the cycles before. The file is undated, one for every cycle from 2010; before 2010
-- the runner gives an empty one, and no committee is flagged. A committee `cm` lacks has no row.
-- filed_date and image_num are the deciding Form 1's.
CREATE TABLE lobbyist_pac AS
WITH filed AS (
    SELECT
        trim(Committee_Id) AS committee_id,
        -- FEC writes DD-MON-YY; a malformed date is null, and so never the latest.
        CAST(try_strptime(Date_Filed, '%d-%b-%y') AS DATE) AS filed_date,
        -- The digits after `?_` (or `?`): 18 on recent filings, 11 on older ones.
        nullif(regexp_extract(Link_Image, '[?]_?([0-9]+)', 1), '') AS image_num,
        coalesce(trim(Is_Lobbyist) = 'Y', false) AS is_lobbyist
    FROM lobbyist
),
latest AS (
    SELECT *
    FROM filed
    WHERE filed_date <= make_date({cycle}, 12, 31)
    QUALIFY row_number() OVER (
        PARTITION BY committee_id
        -- The box last: no image number repeats in the file, so it only makes a tie settle.
        ORDER BY filed_date DESC, TRY_CAST(image_num AS HUGEINT) DESC NULLS LAST, is_lobbyist DESC
    ) = 1
)
SELECT
    CAST({cycle} AS INTEGER) AS cycle,
    committee_id,
    'fec' AS source,
    'US' AS jurisdiction,
    filed_date,
    image_num
FROM latest
WHERE is_lobbyist AND committee_id IN (SELECT committee_id FROM committee);
