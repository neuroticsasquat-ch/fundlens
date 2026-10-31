"""Contributor normalization and the contributor key (spec §6.1–§6.2).

Resolution runs over contributor keys, not contributions: the exact normalized tuple (name, ZIP5,
employer, occupation) a contribution reports. Normalizing is what makes two spellings of one
contributor string one key, so it removes only what never tells two people apart: case, accents,
punctuation, spacing, a title, a generational or professional suffix, and an employer's legal form
or alias. Anything else, a middle initial against a middle name among them, is left to linkage.

The normalizers are pure functions of their input (the alias table they read is a packaged file,
loaded once). `register` makes them DuckDB functions, so the silver SQL applies them to each
distinct value once rather than to every contribution row.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from importlib.resources import files as package_files
from typing import cast

import duckdb
import nameparser
import yaml
from duckdb.func import FunctionNullHandling

# Dropped from a name. nameparser reads a title it knows ahead of the given name or after the
# family comma; one it misses ('SMITH, JOHN DR') lands in the middle name, whence this drops it.
TITLES = frozenset({"MR", "MRS", "MS", "MISS", "DR"})
# Kept as the name's suffix and out of its key. nameparser finds these and more itself; these are
# also taken out of a middle name it left them in.
SUFFIXES = frozenset({"JR", "SR", "II", "III", "IV", "MD", "ESQ", "PHD"})


def clean(raw: str) -> str:
    """`raw` uppercased, accents folded and spacing collapsed, a separator (hyphen, slash,
    ampersand, comma) made a space and any other punctuation deleted: 'Muñoz-Díaz, José' is
    'MUNOZ DIAZ JOSE', and 'J.P.' is 'JP'."""
    folded = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    spaced = re.sub(r"[-/&,]", " ", folded.upper())
    return " ".join(re.sub(r"[^A-Z0-9\s]", "", spaced).split())


def _unspaced(value: str) -> str:
    return value.replace(" ", "")


# An employer or occupation that names no employer or occupation, as filers write it: null. Matched
# with spaces ignored, so 'SELFEMPLOYED' and 'NOT-EMPLOYED' are among them.
NO_VALUE = frozenset(
    _unspaced(clean(value))
    for value in [
        "SELF-EMPLOYED",
        "SELF EMPLOYED",
        "SELF",
        "RETIRED",
        "NOT EMPLOYED",
        "NONE",
        "N/A",
        "INFORMATION REQUESTED",
        "INFORMATION REQUESTED PER BEST EFFORTS",
    ]
)
# An employer's legal form, stripped from its end: 'SPACE EXPLORATION TECHNOLOGIES CORP.'.
LEGAL_FORMS = frozenset(
    {"INC", "INCORPORATED", "LLC", "CORP", "CORPORATION", "LTD", "LIMITED", "CO", "COMPANY"}
)


@dataclass(frozen=True)
class Name:
    """A contributor's name in parts, each cleaned (`clean`) and None when absent."""

    first: str | None
    middle: str | None
    last: str | None
    suffix: str | None

    @property
    def norm(self) -> str:
        """The name as its contributor key spells it, 'LAST, FIRST MIDDLE': no title or suffix,
        so a JR and a SR of one name share it ('' for no name at all)."""
        given = " ".join(part for part in (self.first, self.middle) if part)
        return ", ".join(part for part in (self.last, given) if part)


def normalize_name(raw: str | None) -> Name:
    """`raw`, as FEC writes it ('MARLOWE, AUGUSTINE R. MR.'), parsed into its parts by
    nameparser, the title dropped and the suffix set apart."""
    if raw is None:
        return Name(None, None, None, None)
    parsed = nameparser.parse(raw)
    middle: list[str] = []
    suffix = clean(parsed.suffix).split()
    for token in clean(parsed.middle).split():
        if token in SUFFIXES:
            suffix.append(token)
        elif token not in TITLES:
            middle.append(token)
    return Name(
        first=clean(parsed.given) or None,
        middle=" ".join(middle) or None,
        last=clean(parsed.family) or None,
        suffix=" ".join(suffix) or None,
    )


def zip5(raw: str | None) -> str | None:
    """The five-digit ZIP a ZIP or ZIP+4 begins with ('902501234' is '90250'); None for anything
    else, a foreign postal code or the placeholder '00000' among them."""
    if raw is None:
        return None
    found = re.match(r"\s*(\d{5})", raw)
    if found is None or found[1] == "00000":
        return None
    return found[1]


def _strip_legal_forms(employer: str) -> str:
    words = employer.split()
    while len(words) > 1 and words[-1] in LEGAL_FORMS:
        words.pop()
    return " ".join(words)


def _employer_base(raw: str) -> str | None:
    """`raw` cleaned, nulled when it names no employer, and its legal form stripped."""
    employer = clean(raw)
    if _unspaced(employer) in NO_VALUE or employer in LEGAL_FORMS:
        return None
    return _strip_legal_forms(employer) or None


def _alias_map(document: object) -> dict[str, str]:
    if not isinstance(document, dict):
        raise ValueError("aliases.yaml must map each canonical employer to its spellings")
    aliases: dict[str, str] = {}
    for canonical, spellings in cast(dict[object, object], document).items():
        if not isinstance(canonical, str) or not isinstance(spellings, list):
            raise ValueError(f"aliases.yaml: {canonical!r} must map to a list of spellings")
        if _employer_base(canonical) != canonical:
            raise ValueError(f"aliases.yaml: {canonical!r} is not written as it normalizes")
        for spelling in cast(list[object], spellings):
            base = _employer_base(str(spelling))
            if base is None or base == canonical:
                raise ValueError(f"aliases.yaml: {spelling!r} under {canonical!r} aliases nothing")
            if aliases.setdefault(base, canonical) != canonical:
                raise ValueError(f"aliases.yaml: {spelling!r} is under two employers")
    return aliases


@cache
def employer_aliases() -> dict[str, str]:
    """`aliases.yaml`: each spelling of a top employer, normalized, to its canonical name."""
    text = package_files("fundlens.resolve").joinpath("aliases.yaml").read_text()
    return _alias_map(yaml.safe_load(text))


def normalize_employer(raw: str | None) -> str | None:
    """`raw` cleaned, its legal form stripped and its alias resolved ('Space Exploration
    Technologies Corp.' is 'SPACEX'); None when it names no employer ('SELF-EMPLOYED')."""
    if raw is None:
        return None
    base = _employer_base(raw)
    if base is None:
        return None
    return employer_aliases().get(base, base)


def normalize_occupation(raw: str | None) -> str | None:
    """`raw` cleaned; None when it names no occupation ('RETIRED', 'N/A')."""
    if raw is None:
        return None
    occupation = clean(raw)
    if not occupation or _unspaced(occupation) in NO_VALUE:
        return None
    return occupation


def contributor_key(
    name_norm: str, zip5: str | None, employer_norm: str | None, occupation_norm: str | None
) -> str:
    """The contributor key: the four normalized values joined by '|', an absent one empty
    ('MARLOWE, AUGUSTINE|90250|ASTRAX|CEO'). No normalized value holds a '|', so the key reads
    back unambiguously. sql/silver/04_contribution.sql spells the same key in SQL."""
    return "|".join(part or "" for part in (name_norm, zip5, employer_norm, occupation_norm))


NAME_TYPE = "STRUCT(first VARCHAR, middle VARCHAR, last VARCHAR, suffix VARCHAR, norm VARCHAR)"


def _name_struct(raw: str | None) -> dict[str, str | None]:
    name = normalize_name(raw)
    return {
        "first": name.first,
        "middle": name.middle,
        "last": name.last,
        "suffix": name.suffix,
        "norm": name.norm,
    }


def register(con: duckdb.DuckDBPyConnection) -> None:
    """Make the normalizers DuckDB functions on `con`: `normalize_name` (a struct of the `Name`
    parts and its `norm`), `zip5`, `normalize_employer` and `normalize_occupation`. They see a
    NULL as None, so a NULL name is a struct of NULL parts with an empty `norm`."""
    udfs = (
        ("normalize_name", _name_struct, NAME_TYPE),
        ("zip5", zip5, "VARCHAR"),
        ("normalize_employer", normalize_employer, "VARCHAR"),
        ("normalize_occupation", normalize_occupation, "VARCHAR"),
    )
    for name, function, returns in udfs:
        # DuckDB's stub leaves one overload's return type unknown.
        con.create_function(  # pyright: ignore[reportUnknownMemberType]
            name, function, ["VARCHAR"], returns, null_handling=FunctionNullHandling.SPECIAL
        )
