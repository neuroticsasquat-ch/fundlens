"""Contributor normalization and the contributor key (spec §6.1–§6.2)."""

import duckdb
import pytest

from fundlens.resolve import normalize
from fundlens.resolve.normalize import (
    Name,
    contributor_key,
    is_organization_name,
    is_payee_organization_name,
    normalize_employer,
    normalize_name,
    normalize_occupation,
    organization_key,
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


def test_dotted_initials_norm_as_the_pinned_nameparser_reads_them() -> None:
    # The contributor key is built from the norm, so a nameparser that reads dotted initials another
    # way re-keys contributions: 3.1.0 split them ('SHROLL, C J', 'KELSEY, T D') and re-keyed 11,198
    # of 2024's (NEU-2458). These are 3.0.1's readings, as 2024's live keys hold them. Changing one
    # is a re-keying decision, not a dependency bump.
    names = ["SHROLL, C.J.", "KELSEY, T.D.", "WILLIAMS, J.D.", "CRAIN, M.D., LUCYS"]
    assert {raw: normalize_name(raw).norm for raw in names} == {
        "SHROLL, C.J.": "SHROLL, CJ",
        "KELSEY, T.D.": "KELSEY",
        "WILLIAMS, J.D.": "WILLIAMS",
        "CRAIN, M.D., LUCYS": "CRAIN",
    }


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The employer rule: cleaned, the legal form stripped, the alias applied (ADR-0011).
        ("KOCH INDUSTRIES, INC.", "KOCH INDUSTRIES"),
        ("KOCH INDUSTRIES INC", "KOCH INDUSTRIES"),
        ("Koch Industries", "KOCH INDUSTRIES"),
        ("Space Exploration Technologies Corp.", "SPACEX"),
        ("IRONWORKERS LOCAL 16", "IRONWORKERS LOCAL 16"),
        ("ACME HOLDINGS, L.L.C.", "ACME HOLDINGS"),
        # The payee key is the organization key (ADR-0012), so a split payee is one key by alias
        # (spec §5.4, NEU-2460, NEU-2461, NEU-2462, NEU-2463).
        ("AXMEDIA", "AX MEDIA"),
        ("AXMEDIA LLC", "AX MEDIA"),
        ("AX MEDIA", "AX MEDIA"),
        ("TEAMDIRECT", "TEAM DIRECT"),
        ("TEAMDIRECT LLC", "TEAM DIRECT"),
        ("TEAM DIRECT", "TEAM DIRECT"),
        ("MISSIONWIRED", "MISSIONWIRED"),
        ("ANNE LEWIS STRATEGIES", "MISSIONWIRED"),
        ("Anne Lewis Strategies, LLC", "MISSIONWIRED"),
        ("ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED", "MISSIONWIRED"),
        ("MISSION WIRED", "MISSIONWIRED"),
        # Firms written with and without a space (NEU-2463).
        ("ON MESSAGE", "ONMESSAGE"),
        ("On Message, Inc.", "ONMESSAGE"),
        ("ONMESSAGE", "ONMESSAGE"),
        ("SKD KNICKERBOCKER", "SKDKNICKERBOCKER"),
        ("SKD Knickerbocker LLC", "SKDKNICKERBOCKER"),
        ("SKDKNICKERBOCKER", "SKDKNICKERBOCKER"),
        ("WIN RED TECHNICAL SERVICES", "WINRED TECHNICAL SERVICES"),
        ("WinRed Technical Services LLC", "WINRED TECHNICAL SERVICES"),
        ("WINRED TECHNICAL SERVICES", "WINRED TECHNICAL SERVICES"),
        ("WIN RED", "WINRED"),
        ("WinRed, Inc.", "WINRED"),
        ("WINRED", "WINRED"),
        ("ACT BLUE TECHNICAL SERVICES", "ACTBLUE TECHNICAL SERVICES"),
        ("ACTBLUE TECHNICAL SERVICES", "ACTBLUE TECHNICAL SERVICES"),
        ("BRABENDER COX", "BRABENDERCOX"),
        ("BRABENDERCOX", "BRABENDERCOX"),
        ("DONOR BUREAU", "DONORBUREAU"),
        ("Donor Bureau LLC", "DONORBUREAU"),
        ("DONORBUREAU", "DONORBUREAU"),
        ("ABDATA", "AB DATA"),
        ("AB DATA", "AB DATA"),
        ("GRASS ROOTS MEDIA", "GRASSROOTS MEDIA"),
        ("GRASSROOTS MEDIA", "GRASSROOTS MEDIA"),
        # Firms trading under a second name, under the key with the most payee dollars (NEU-2463).
        ("ALG POLLING", "IMPACT RESEARCH"),
        ("ALG POLLING, INC. DBA IMPACT RESEARCH", "IMPACT RESEARCH"),
        ("ALG POLLING, INC. D/B/A IMPACT RESEARCH, INC.", "IMPACT RESEARCH"),
        ("IMPACT RESEARCH, INC.", "IMPACT RESEARCH"),
        ("YANG STRATEGIC RESEARCH LLC", "HART RESEARCH ASSOCIATES"),
        ("YANG STRATEGIC RESEARCH LLC DBA HART RESEARCH ASSOCIATES", "HART RESEARCH ASSOCIATES"),
        ("YANG STRATEGIC RESEARCH LLC D/B/A HART RESEARCH ASSOCIATES", "HART RESEARCH ASSOCIATES"),
        ("YANG STRATEGIC RESEARCH LLC D/B/A HART RESEARCH", "HART RESEARCH ASSOCIATES"),
        ("HART RESEARCH ASSOCIATES YANG STRATEGIC RESEARCH LLC", "HART RESEARCH ASSOCIATES"),
        ("HART RESEARCH ASSOCIATES", "HART RESEARCH ASSOCIATES"),
        ("REID POLITICAL CONSULTING", "REPUBLIC STRATEGIES"),
        ("REID POLITICAL CONSULTING, LLC DBA REPUBLIC STRATEGIES, LLC", "REPUBLIC STRATEGIES"),
        ("REPUBLIC STRATEGIES/REID POLITICAL CONSULTING LLC", "REPUBLIC STRATEGIES"),
        ("REPUBLIC STRATEGIES", "REPUBLIC STRATEGIES"),
        ("TMONE LLC", "TMONE LLC DBA MASS MARKETS"),
        ("MASS MARKETS", "MASS MARKETS"),
        ("TMONW LLC DBA MASS MARKETS", "TMONE LLC DBA MASS MARKETS"),
        ("TIMONE LLC DBA MASS MARKETS", "TMONE LLC DBA MASS MARKETS"),
        ("TMONE LLC DBA MASS MARKETS", "TMONE LLC DBA MASS MARKETS"),
        ("TRUVERSE, INC.", "TRUVERSE INC DBA AMPLIFYAI"),
        ("TRUVERSE/AMPLIFY.AI", "TRUVERSE INC DBA AMPLIFYAI"),
        ("AMPLIFY.AI", "TRUVERSE INC DBA AMPLIFYAI"),
        ("TRUVERSE, INC. DBA AMPLIFY.AI", "TRUVERSE INC DBA AMPLIFYAI"),
        # A name the employer rule nulls keeps the cleaned name as its key: a receipt always has
        # one.
        ("NONE", "NONE"),
        ("N/A", "N A"),
        ("INC", "INC"),
        # No name at all is no key.
        (None, None),
        ("", None),
        (" . ", None),
    ],
)
def test_organization_key(raw: str | None, expected: str | None) -> None:
    assert organization_key(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The measurement's Decisions table (NEU-2129), with the call the rule makes, not what the
        # name really is. A word alone in its comma-separated part is a person's name.
        ("BANK, LISSY", False),
        ("WOOTEN, COUNCIL", False),
        ("NATION, MARK", False),
        # CO, COMPANY, PC and LP end people's names: not strict legal suffixes.
        ("COX, JOHN T. MR. III PC", False),
        ("PERRETT, LP", False),
        ("WEITZ & LUXENBERG, P.C.", False),
        # A hyphen splits a part into two words.
        ("LEAGUE-PASCUAL, JAMES", True),
        ("LARSON, BEV MS. LLC", True),
        ("SMITH, PATRICIA J LLC", True),
        # No comma.
        (" UPDIKE", True),
        ("LOFTUS", True),
        ("FUTURE FORWARD USA ACTION", True),
        # COUNCIL and NATION are not organization words.
        ("TRIBAL COUNCIL, PRAIRIE ISLAND", False),
        ("NATION, CHEROKEE", False),
        ("NEA ADVOCACY FUND, ASSOCIATION", True),
        # Periods are deleted, so the last word is LLC.
        ("ACME HOLDINGS, L.L.C.", True),
        ("LEAGUE OF CONSERVATION VOTERS, INC.", True),
        # The fixture's blank-entity-type rows.
        ("ACME WIDGETS INC", True),
        ("BANKS, JOHN", False),
        ("OLD LINE REPUBLICAN COMMITTEE", True),
        # No name, or one of no words, is not an organization.
        (None, False),
        ("", False),
        (" . ", False),
    ],
)
def test_is_organization_name(raw: str | None, expected: bool) -> None:
    assert is_organization_name(raw) is expected


@pytest.mark.parametrize(
    "raw",
    [
        # The firms 2018's blank-type payee rows lost their pages under (NEU-2541).
        "CHAIN BRIDGE BANK, N.A.",
        "DEMOCRACY ENGINE, INC. PAC",
        "VERDOLINO & LOWEY, P.C.",
        "FAIRBANK, MASLIN, MAULIN, METZ & ASSOCIATES",
        "IMAGE DIRECT,LLN",
        "MERKLE RESPONSE SERVICES ,LNC",
        "IMPREMEDIA OPERATING COMPANY, LLC DBA LA OPINION",
        "MARCUS,CLEGG,BALS & ROSENTHAL,PA",
        # A P.C. ends a firm's name among payees, where the contributor classifier reads a person's.
        "WEITZ & LUXENBERG, P.C.",
        # Whatever the contributor classifier calls an organization, this one does too.
        "ACME HOLDINGS, L.L.C.",
        "NEA ADVOCACY FUND, ASSOCIATION",
        "HARBORVIEW DIGITAL",
    ],
)
def test_a_payee_name_with_a_payee_suffix_is_an_organization(raw: str) -> None:
    assert is_payee_organization_name(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "SMITH, JOHN",
        "COX, JOHN T. MR. III",
        "BANK, LISSY",
        # CPA ends people's names among payees too (2018: a third of its filed dollars are IND).
        "BLACKMAN, PERRY CPA",
        # A suffix's word inside a name, not at its end or before a PAC or DBA.
        "GROUPER, ANN",
        "SMITH, PAC MAN",
        None,
        "",
        " . ",
    ],
)
def test_a_payee_name_without_one_stays_a_person(raw: str | None) -> None:
    assert not is_payee_organization_name(raw)


def test_payee_suffix_names_the_suffix_that_decides() -> None:
    assert normalize.payee_suffix("CHAIN BRIDGE BANK, N.A.") == "NA"
    assert normalize.payee_suffix("DEMOCRACY ENGINE, INC. PAC") == "PAC"
    assert normalize.payee_suffix("IMPREMEDIA OPERATING COMPANY, LLC DBA LA OPINION") == "LLC"
    assert normalize.payee_suffix("SMITH, JOHN") is None
    assert normalize.payee_suffix(None) is None


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
            " normalize_occupation('RETIRED'), normalize_name(NULL),"
            " organization_key('Koch Industries, Inc.'), organization_key(NULL),"
            " is_organization_name('ACME WIDGETS INC'), is_organization_name(NULL),"
            " is_payee_organization_name('VERDOLINO & LOWEY, P.C.'),"
            " is_payee_organization_name(NULL)"
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
        "KOCH INDUSTRIES",
        None,
        True,
        False,
        True,
        False,
    )
