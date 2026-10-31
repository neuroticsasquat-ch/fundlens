"""Contributor normalization and the contributor key (spec §6.1–§6.2)."""

import duckdb
import pytest

from fundlens.resolve import normalize
from fundlens.resolve.normalize import (
    Name,
    contributor_key,
    normalize_employer,
    normalize_name,
    normalize_occupation,
    zip5,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MARLOWE, AUGUSTINE", Name("AUGUSTINE", None, "MARLOWE", None)),
        ("Marlowe, Augustine", Name("AUGUSTINE", None, "MARLOWE", None)),
        ("MARLOWE,AUGUSTINE JR.", Name("AUGUSTINE", None, "MARLOWE", "JR")),
        ("MARLOWE, AUGUSTINE R.", Name("AUGUSTINE", "R", "MARLOWE", None)),
        ("MARLOWE, AUGUSTINE REEVE", Name("AUGUSTINE", "REEVE", "MARLOWE", None)),
        # A title goes, ahead of the given name or after it, known to nameparser or not.
        ("MARLOWE, AUGUSTINE MR.", Name("AUGUSTINE", None, "MARLOWE", None)),
        ("WHITLOCK, GORDON R. MR", Name("GORDON", "R", "WHITLOCK", None)),
        ("SMITH, DR JOHN", Name("JOHN", None, "SMITH", None)),
        ("SMITH, JOHN DR", Name("JOHN", None, "SMITH", None)),
        ("HARGROVE, ELLEN MRS.", Name("ELLEN", None, "HARGROVE", None)),
        # Every listed suffix is set apart, however written.
        ("ABERNATHY, CHARLES SR", Name("CHARLES", None, "ABERNATHY", "SR")),
        ("SMITH, JOHN II", Name("JOHN", None, "SMITH", "II")),
        ("O'BRIEN, PATRICK J III", Name("PATRICK", "J", "OBRIEN", "III")),
        ("SMITH, JOHN IV", Name("JOHN", None, "SMITH", "IV")),
        ("DOE, JANE M.D.", Name("JANE", None, "DOE", "MD")),
        ("DOE, JANE ESQ.", Name("JANE", None, "DOE", "ESQ")),
        ("DOE, JANE PH.D.", Name("JANE", None, "DOE", "PHD")),
        ("SMITH JR, JOHN", Name("JOHN", None, "SMITH", "JR")),
        ("SMITH, JOHN JR MD", Name("JOHN", None, "SMITH", "JR MD")),
        # A hyphen is a space, other punctuation goes, accents fold; a particle stays in the family
        # name.
        ("SMITH-JONES, ANNE MARIE", Name("ANNE", "MARIE", "SMITH JONES", None)),
        ("MUÑOZ, JOSÉ", Name("JOSE", None, "MUNOZ", None)),
        ("VAN DYKE, MARY ANN", Name("MARY", "ANN", "VAN DYKE", None)),
        ('SMITH, ROBERT "BOB"', Name("ROBERT", None, "SMITH", None)),
        ("", Name(None, None, None, None)),
        (None, Name(None, None, None, None)),
    ],
)
def test_normalize_name(raw: str | None, expected: Name) -> None:
    assert normalize_name(raw) == expected


def test_a_names_norm_is_last_then_given_without_title_or_suffix() -> None:
    assert normalize_name("O'Brien, Patrick J. III").norm == "OBRIEN, PATRICK J"
    assert normalize_name("MARLOWE, AUGUSTINE").norm == "MARLOWE, AUGUSTINE"
    assert normalize_name("ACME").norm == "ACME"
    assert normalize_name(None).norm == ""


def test_name_variants_differing_only_by_punctuation_suffix_or_title_share_a_norm() -> None:
    variants = [
        "MARLOWE, AUGUSTINE",
        "MARLOWE,AUGUSTINE JR.",
        "Marlowe, Augustine",
        "MARLOWE, AUGUSTINE MR.",
        "MARLOWE , AUGUSTINE, SR",
    ]
    assert {normalize_name(raw).norm for raw in variants} == {"MARLOWE, AUGUSTINE"}
    # A middle initial is not punctuation: linkage, not normalization, decides that one.
    assert normalize_name("MARLOWE, AUGUSTINE R.").norm == "MARLOWE, AUGUSTINE R"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("90250", "90250"),
        ("902501234", "90250"),
        ("90250-1234", "90250"),
        (" 02139", "02139"),
        ("2139", None),
        ("00000", None),
        ("K1A 0B6", None),
        ("", None),
        (None, None),
    ],
)
def test_zip5(raw: str | None, expected: str | None) -> None:
    assert zip5(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "SELF-EMPLOYED",
        "Self Employed",
        "SELFEMPLOYED",
        "SELF",
        "RETIRED",
        "NOT EMPLOYED",
        "NOT-EMPLOYED",
        "NONE",
        "N/A",
        "NA",
        "INFORMATION REQUESTED",
        "INFORMATION REQUESTED PER BEST EFFORTS",
        "  ",
        "INC.",
        None,
    ],
)
def test_an_employer_naming_no_employer_is_null(raw: str | None) -> None:
    assert normalize_employer(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The legal form goes from the end, however many there are, but never the whole name.
        ("ACME WIDGETS, INC.", "ACME WIDGETS"),
        ("Acme Widgets LLC", "ACME WIDGETS"),
        ("ACME WIDGETS CORP", "ACME WIDGETS"),
        ("ACME WIDGETS LTD.", "ACME WIDGETS"),
        ("WELLS FARGO & CO.", "WELLS FARGO"),
        ("ACME CO INC", "ACME"),
        ("CO OP BANK", "CO OP BANK"),
        ("  SMITH   &   COLE  LLP ", "SMITH COLE LLP"),
        ("AT&T", "AT T"),
        ("AT & T", "AT T"),
        # An alias resolves after the legal form is stripped.
        ("Space Exploration Technologies Corp.", "SPACEX"),
        ("SPACE EXPLORATION TECHNOLOGIES", "SPACEX"),
        ("SPACEX", "SPACEX"),
        ("Space-X", "SPACEX"),
        ("Tesla, Inc.", "TESLA"),
        ("AMAZON.COM", "AMAZON"),
        ("J.P. MORGAN", "JPMORGAN CHASE"),
        ("ASTRA EXPLORATION TECHNOLOGIES", "ASTRAX"),
    ],
)
def test_normalize_employer(raw: str, expected: str) -> None:
    assert normalize_employer(raw) == expected


def test_spacex_variants_map_to_one_canonical_employer() -> None:
    assert normalize_employer("Space Exploration Technologies Corp.") == normalize_employer(
        "SPACEX"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Chief Engineer", "CHIEF ENGINEER"),
        ("C.E.O.", "CEO"),
        ("  REAL   ESTATE ", "REAL ESTATE"),
        ("RETIRED", None),
        ("SELF-EMPLOYED", None),
        ("N/A", None),
        ("NOT-EMPLOYED", None),
        ("INFORMATION REQUESTED", None),
        ("", None),
        (None, None),
        # Legal forms and aliases are an employer's alone.
        ("CO", "CO"),
    ],
)
def test_normalize_occupation(raw: str | None, expected: str | None) -> None:
    assert normalize_occupation(raw) == expected


def test_contributor_key_joins_the_four_values_with_an_absent_one_empty() -> None:
    assert (
        contributor_key("MARLOWE, AUGUSTINE", "90250", "ASTRAX", "CEO")
        == "MARLOWE, AUGUSTINE|90250|ASTRAX|CEO"
    )
    assert contributor_key("SMITH, JOHN", "21201", None, None) == "SMITH, JOHN|21201||"
    assert contributor_key("", None, None, None) == "|||"


def test_the_shipped_alias_file_loads() -> None:
    aliases = normalize.employer_aliases()
    assert aliases["SPACE EXPLORATION TECHNOLOGIES"] == "SPACEX"
    assert "SPACEX" not in aliases


@pytest.mark.parametrize(
    ("document", "complaint"),
    [
        (["SPACEX"], "must map each canonical"),
        ({"SPACEX": "SPACE X"}, "list of spellings"),
        ({"SpaceX": ["Space X"]}, "not written as it normalizes"),
        ({"SPACEX": ["SpaceX Inc."]}, "aliases nothing"),
        ({"SPACEX": ["Space X"], "SPACE": ["SPACE X"]}, "under two employers"),
    ],
)
def test_a_malformed_alias_file_is_refused(document: object, complaint: str) -> None:
    with pytest.raises(ValueError, match=complaint):
        normalize._alias_map(document)  # pyright: ignore[reportPrivateUsage]


def test_the_normalizers_are_duckdb_functions_once_registered() -> None:
    with duckdb.connect() as con:
        normalize.register(con)
        row = con.execute(
            "SELECT normalize_name('MARLOWE,AUGUSTINE JR.'), zip5('902501234'),"
            " normalize_employer('Space Exploration Technologies Corp.'),"
            " normalize_occupation('RETIRED'), normalize_name(NULL)"
        ).fetchone()
    assert row == (
        {
            "first": "AUGUSTINE",
            "middle": None,
            "last": "MARLOWE",
            "suffix": "JR",
            "norm": "MARLOWE, AUGUSTINE",
        },
        "90250",
        "SPACEX",
        None,
        {"first": None, "middle": None, "last": None, "suffix": None, "norm": ""},
    )
