"""The Splink model that links contributor keys into one person (spec §6.3).

A Fellegi-Sunter model over the `contributor` table, deduplicating it with Splink's DuckDB
backend: three blocking rules choose the pairs worth scoring, and six comparisons score each.
Every comparison level starts from a prior m and u probability, the model's parameters before it
has seen data and the ones it keeps for any level training cannot estimate. `train` estimates the
rest from the contributors themselves.

The priors encode what the fixture's hard cases assert (spec §6). A name agreeing in full is the
strongest evidence there is; a different first name is a different person to linkage, since a
nickname (PEGGY for MARGARET) is an override's or an adjudication's to merge (§6.5, §6.8), and
two people of one household share a surname, a ZIP and often an employer. So a first name that
disagrees outright all but vetoes a match, whatever else agrees, and training never moves it.
"""

import logging
from typing import Any

import duckdb
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from duckdb.func import FunctionNullHandling
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

log = logging.getLogger(__name__)

# The pairs prediction scores (spec §6.3): a surname that sounds alike in one three-digit ZIP
# area, a surname and first initial in one state, and a surname at one employer.
BLOCKING_RULES = (
    block_on("last_name_soundex", "zip3"),
    block_on("last_name", "first_initial", "state"),
    block_on("employer_norm", "last_name"),
)

# The probability two random keys are one person is the count of pairs these rules match, which
# admit almost no false match, scaled up by the share of true matches they are thought to find.
# Most of a person's keys share a name and ZIP; the rest moved, or wrote another address.
DETERMINISTIC_RULES = (block_on("first_name", "last_name", "zip5"),)
DETERMINISTIC_RECALL = 0.6

# Pairs sampled to estimate u: Splink's advice is 1e7 to 1e9, more being slower and closer.
U_MAX_PAIRS = 1e8
U_SEED = 2048


def _first_name() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="first_name",
        comparison_levels=[
            cll.NullLevel("first_name"),
            cll.ExactMatchLevel("first_name").configure(m_probability=0.88, u_probability=0.005),
            cll.JaroWinklerLevel("first_name", 0.92).configure(
                m_probability=0.07, u_probability=0.003
            ),
            cll.JaroWinklerLevel("first_name", 0.8).configure(
                m_probability=0.03, u_probability=0.01
            ),
            # 'A' for 'AUGUSTINE'.
            cll.ExactMatchLevel("first_initial").configure(m_probability=0.02, u_probability=0.03),
            # The veto: a first name that differs outright is a different person. Fixed, so EM
            # cannot learn a household's members as one person and lift it.
            cll.ElseLevel().configure(
                m_probability=1e-10, u_probability=0.952, fix_m_probability=True
            ),
        ],
    )


def _last_name() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="last_name",
        comparison_levels=[
            cll.NullLevel("last_name"),
            cll.ExactMatchLevel("last_name").configure(m_probability=0.95, u_probability=0.0005),
            cll.JaroWinklerLevel("last_name", 0.92).configure(
                m_probability=0.03, u_probability=0.002
            ),
            # A surname changed by marriage.
            cll.ElseLevel().configure(m_probability=0.02, u_probability=0.9975),
        ],
    )


def _zip5() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="zip5",
        comparison_levels=[
            cll.NullLevel("zip5"),
            cll.ExactMatchLevel("zip5").configure(m_probability=0.65, u_probability=0.0005),
            cll.ExactMatchLevel("zip3").configure(m_probability=0.1, u_probability=0.01),
            # A donor who moved, or gave from home and from the office.
            cll.ElseLevel().configure(m_probability=0.25, u_probability=0.9895),
        ],
    )


def _city_state() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="city_state",
        comparison_levels=[
            cll.Or(cll.NullLevel("city"), cll.NullLevel("state")),
            cll.And(cll.ExactMatchLevel("city"), cll.ExactMatchLevel("state")).configure(
                m_probability=0.65, u_probability=0.002
            ),
            cll.ExactMatchLevel("state").configure(m_probability=0.15, u_probability=0.04),
            cll.ElseLevel().configure(m_probability=0.2, u_probability=0.958),
        ],
    )


def _employer() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="employer_norm",
        comparison_levels=[
            cll.NullLevel("employer_norm"),
            cll.ExactMatchLevel("employer_norm").configure(m_probability=0.6, u_probability=0.001),
            cll.JaroWinklerLevel("employer_norm", 0.9).configure(
                m_probability=0.1, u_probability=0.002
            ),
            cll.ElseLevel().configure(m_probability=0.3, u_probability=0.997),
        ],
    )


def _occupation() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="occupation_norm",
        comparison_levels=[
            cll.NullLevel("occupation_norm"),
            cll.ExactMatchLevel("occupation_norm").configure(m_probability=0.6, u_probability=0.02),
            cll.ElseLevel().configure(m_probability=0.4, u_probability=0.98),
        ],
    )


def settings() -> SettingsCreator:
    """The untrained model: blocking rules, comparisons and their priors (spec §6.3)."""
    return SettingsCreator(
        link_type="dedupe_only",
        unique_id_column_name="contributor_key",
        blocking_rules_to_generate_predictions=list(BLOCKING_RULES),
        comparisons=[
            _first_name(),
            _last_name(),
            _zip5(),
            _city_state(),
            _employer(),
            _occupation(),
        ],
        # A prediction is the pair and its probability: the crosswalk needs nothing else.
        retain_matching_columns=False,
        retain_intermediate_calculation_columns=False,
    )


# American Soundex digits; a vowel, H, W and Y have none.
_SOUNDEX = {
    **dict.fromkeys("BFPV", "1"),
    **dict.fromkeys("CGJKQSXZ", "2"),
    **dict.fromkeys("DT", "3"),
    "L": "4",
    **dict.fromkeys("MN", "5"),
    "R": "6",
}


def soundex(name: str | None) -> str | None:
    """`name`'s American Soundex code ('ROBERT' and 'RUPERT' are 'R163'); None when it has no
    letter. DuckDB has no soundex of its own."""
    if name is None:
        return None
    letters = [char for char in name.upper() if "A" <= char <= "Z"]
    if not letters:
        return None
    code = [letters[0]]
    previous = _SOUNDEX.get(letters[0], "")
    for char in letters[1:]:
        digit = _SOUNDEX.get(char, "")
        if digit and digit != previous:
            code.append(digit)
        # H and W do not separate two letters of one digit; a vowel does.
        if char not in "HW":
            previous = digit
    return ("".join(code) + "000")[:4]


def register(con: duckdb.DuckDBPyConnection) -> None:
    """Make `soundex` a DuckDB function on `con`."""
    # DuckDB's stub leaves one overload's return type unknown.
    con.create_function(  # pyright: ignore[reportUnknownMemberType]
        "soundex", soundex, ["VARCHAR"], "VARCHAR", null_handling=FunctionNullHandling.SPECIAL
    )


def linker(db_api: DuckDBAPI, table: str, model: SettingsCreator | dict[str, Any]) -> Linker:
    """A linker over the contributor table `table` (one row per key, in the columns the
    comparisons read): the untrained `settings()`, or a trained model read back from its JSON."""
    # log_level None: Splink's messages go through fundlens's logging, not a handler of its own.
    # Splink's stub leaves one of `register`'s input types unknown.
    registered = db_api.register(table)  # pyright: ignore[reportUnknownMemberType]
    return Linker(registered, model, log_level=None)


def train(linker: Linker, *, keys: int, min_training_keys: int) -> bool:
    """Train `linker`'s model on its contributors (spec §6.3); whether u and m were estimated.

    The probability two random keys match is always estimated, by counting deterministic
    matches. u is estimated by random sampling and m by expectation maximisation on each
    blocking rule only when there are at least `min_training_keys` keys: on fewer, a random
    sample measures how often the sample's few surnames collide, not the population's, and EM
    takes a household for a person. The model then keeps its priors for both.
    """
    linker.training.estimate_probability_two_random_records_match(
        list(DETERMINISTIC_RULES), recall=DETERMINISTIC_RECALL
    )
    if keys < min_training_keys:
        log.info(
            "resolve: %d contributor keys, under the %d to train on; u and m keep their priors",
            keys,
            min_training_keys,
        )
        return False
    linker.training.estimate_u_using_random_sampling(max_pairs=U_MAX_PAIRS, seed=U_SEED)
    for rule in BLOCKING_RULES:
        linker.training.estimate_parameters_using_expectation_maximisation(rule)
    return True
