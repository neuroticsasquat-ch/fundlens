"""The vendored list of independent expenditures `pas2` codes to the wrong candidate (NEU-2279)."""

import csv
import io
import re
from importlib.resources import files as package_files

CANDIDATE_ID = re.compile(r"[HSP][0-9A-Z]{8}")
# Future Forward's three lines against TRUMP, filed with his id, which `pas2` codes BIDEN's.
FUTURE_FORWARD = {"4060220251204384139", "4060220251204384159", "4060220251204384180"}
TRUMP, BIDEN = "P80001571", "P80000722"


def corrections() -> list[dict[str, str]]:
    text = package_files("fundlens.fec").joinpath("ie_candidate_corrections.csv").read_text()
    return list(csv.DictReader(io.StringIO(text)))


def test_each_row_is_corrected_once_to_another_candidate_with_its_filing_cited() -> None:
    rows = corrections()

    assert len({row["sub_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["sub_id"].isdigit(), row
        assert CANDIDATE_ID.fullmatch(row["pas2_candidate_id"]), row
        assert CANDIDATE_ID.fullmatch(row["candidate_id"]), row
        assert row["candidate_id"] != row["pas2_candidate_id"], row
        assert row["source"].startswith("filing "), row


def test_future_forwards_spending_against_trump_is_his() -> None:
    listed = {row["sub_id"]: row for row in corrections() if row["sub_id"] in FUTURE_FORWARD}

    assert {(r["pas2_candidate_id"], r["candidate_id"]) for r in listed.values()} == {
        (BIDEN, TRUMP)
    }
    assert listed.keys() == FUTURE_FORWARD
