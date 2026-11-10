-- No conduit's total_individual is below -$1M. A conduit's own money is its tips, net of the
-- tips it refunds; its refunds of earmarks are dropped, since the earmarks count at their
-- recipients alone (ADR-0004), and WinRed's put it at -$48.2M on 2024 until NEU-2199. Other
-- committees are not held to it: a candidate who retires refunds gifts of earlier cycles, as
-- Manchin's and Sinema's campaigns did in 2024 (-$2.3M and -$1.4M), and those are real.
SELECT committee_cycle.committee_id, committee_cycle.total_individual
FROM committee_cycle
JOIN committee USING (committee_id)
WHERE committee.is_conduit AND committee_cycle.total_individual < -1000000;
