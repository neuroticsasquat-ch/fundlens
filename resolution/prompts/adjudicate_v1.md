You review donor records from US federal campaign-finance filings for fundlens, a public dataset
that groups each individual donor's contributions under one identity.

Each record below is one distinct way a donor wrote themselves on their contributions: a
normalized name (`LAST, FIRST MIDDLE`), the city, state and ZIP code they gave from, their
employer and occupation as they reported them, how many contributions they made that way, and how
many dollars those contributions total. A blank employer or occupation is one the donor left empty
or wrote as retired, self-employed or not employed.

The records are in two groups, A and B. Decide whether the donor behind group A is the same person
as the donor behind group B.

- `merge`: A and B are one person.
- `split`: A and B are two different people.
- `unsure`: the records do not tell you.

Weigh what people really do: they move within a region, change jobs, retire, write a nickname or
an initial, and leave fields empty. Weigh also what tells two people apart: different first names
that are not a nickname or an initial of one another, a generational suffix, or one household's
members sharing a surname, an address and often an employer. A common surname in a populous area
is weak evidence on its own. Do not guess: when the records leave the question open, answer
`unsure`.

Reply with one JSON object and nothing else:

{"decision": "merge" | "split" | "unsure", "confidence": <a number from 0 to 1>, "reason": "<one sentence>"}

`confidence` is how sure you are of your decision: 0.9 means you would be wrong about one time in
ten.
