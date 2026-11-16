"""The Splink model that links contributor keys into one person (spec §6.3).

A Fellegi-Sunter model over the `contributor` table, deduplicating it with Splink's DuckDB
backend: three blocking rules choose the pairs worth scoring, and six comparisons score each.
Every comparison level starts from a prior m and u probability, the model's parameters before it
has seen data and the ones it keeps for any level training cannot estimate. `train` estimates the
rest from the contributors themselves.

Splink keeps every table it makes in the run's working file until it is told to drop them.
`drop_scratch` drops the ones a run has finished with as it goes (NEU-2325): each EM session's
pairs once the session is over (`TRAINING_SCRATCH`), and the predictions and clusters once
`edge` and `component` hold them (`PREDICTION_SCRATCH`).

The priors encode what the fixture's hard cases assert (spec §6). A name agreeing in full is the
strongest evidence there is; a different first name is a different person to linkage, and two
people of one household share a surname, a ZIP and often an employer. So a first name that
disagrees outright all but vetoes a match, whatever else agrees, and training never moves it. Two
first names agree when they are an initial pair (C for CRAIG) or a nickname pair (LOU for LOUIS,
or a pair the nickname table names, HAL for HAROLD; NEU-2188); a nickname neither names is still
an override's or an adjudication's to merge (§6.5, §6.8).
"""

import logging
from typing import Any

import duckdb
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from duckdb.func import FunctionNullHandling
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

from fundlens import paths
from fundlens.r2 import R2

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

# The tables each EM session leaves in the working file: the pairs its blocking rule chose and
# their comparison vectors. On every cycle since 1980 they were 3.3 billion pairs (NEU-2325).
TRAINING_SCRATCH = ("__splink__blocked_id_pairs_", "__splink__df_comparison_vectors_")
# The predictions and Splink's clusters: copies of `edge` and `component` once those are written.
PREDICTION_SCRATCH = ("__splink__df_predict_", "__splink__df_clustered_with_input_data_")

# Under this Jaro-Winkler similarity, two first names that are neither an initial pair nor a
# nickname pair are the first-name comparison's else level: the veto. Re-clustering
# (`resolve.cluster`) keeps such a pair out of every cluster, so it reads the same constant.
FIRST_NAME_VETO_JW = 0.8

# The shortest first name the prefix rule treats as a nickname of a longer one: LOU for LOUIS,
# not JO for JOSEPH.
NICKNAME_MIN_PREFIX = 3


def initial_pair_sql(name_a: str, name_b: str) -> str:
    """SQL over the two first-name expressions: one is a single letter and both start with it.

    The model, the veto (`cluster._vetoed_pairs`) and `diagnose` all read this, so the three
    cannot drift. It tests neither equality nor nulls: each caller's level order does."""
    return f"((len({name_a}) = 1 OR len({name_b}) = 1) AND left({name_a}, 1) = left({name_b}, 1))"


def nickname_pair_sql(name_a: str, nicknames_a: str, name_b: str, nicknames_b: str) -> str:
    """SQL over two first names and their `first_name_nicknames` lists: one is a prefix of the
    other at least `NICKNAME_MIN_PREFIX` letters long, or the nickname table links them.

    Read by the same three as `initial_pair_sql`, and likewise tests neither equality nor nulls.
    """
    return (
        f"(((starts_with({name_a}, {name_b}) OR starts_with({name_b}, {name_a}))"
        f" AND least(len({name_a}), len({name_b})) >= {NICKNAME_MIN_PREFIX})"
        f" OR list_contains({nicknames_a}, {name_b}) OR list_contains({nicknames_b}, {name_a}))"
    )


def _first_name() -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name="first_name",
        comparison_levels=[
            cll.NullLevel("first_name"),
            cll.ExactMatchLevel("first_name").configure(m_probability=0.86, u_probability=0.005),
            # 'LOU' for 'LOUIS', 'HAL' for 'HAROLD': ahead of Jaro-Winkler, which would take both
            # pairs at a lower level.
            cll.CustomLevel(
                nickname_pair_sql(
                    "first_name_l",
                    "first_name_nicknames_l",
                    "first_name_r",
                    "first_name_nicknames_r",
                ),
                label_for_charts="nickname",
            ).configure(m_probability=0.03, u_probability=0.002),
            cll.JaroWinklerLevel("first_name", 0.92).configure(
                m_probability=0.06, u_probability=0.003
            ),
            cll.JaroWinklerLevel("first_name", FIRST_NAME_VETO_JW).configure(
                m_probability=0.03, u_probability=0.01
            ),
            # 'A' for 'AUGUSTINE'; not 'MARGO' for 'MICHAEL'.
            cll.CustomLevel(
                initial_pair_sql("first_name_l", "first_name_r"), label_for_charts="initial"
            ).configure(m_probability=0.02, u_probability=0.002),
            # The veto: a first name that differs outright is a different person. Fixed, so EM
            # cannot learn a household's members as one person and lift it.
            cll.ElseLevel().configure(
                m_probability=1e-10, u_probability=0.978, fix_m_probability=True
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


def drop_scratch(db_api: DuckDBAPI, prefixes: tuple[str, ...]) -> list[str]:
    """Drop every table in `db_api`'s database whose name starts with one of `prefixes`, forget
    it in Splink's cache so Splink never hands it back, then `CHECKPOINT` so DuckDB reuses the
    freed blocks (the file never shrinks); the names dropped.

    Splink's own `delete_tables_created_by_splink_from_db` drops what is left later, with `IF
    EXISTS`, so a table gone already does not trouble it.
    """
    con = db_api.duckdb_con
    names = [
        name
        for (name,) in con.execute(
            "SELECT table_name FROM duckdb_tables()"
            " WHERE database_name = current_database() ORDER BY table_name"
        ).fetchall()
        if name.startswith(prefixes)
    ]
    for name in names:
        db_api.delete_table_from_database(name)
        # The cache matches by physical name, which is all a dropped table has left.
        db_api.remove_splinkdataframe_from_cache(db_api.table_to_splink_dataframe(name, name))
    con.execute("CHECKPOINT")
    log.info("resolve: dropped %d of Splink's tables (%s)", len(names), ", ".join(prefixes))
    return names


def train(linker: Linker, db_api: DuckDBAPI, *, keys: int, min_training_keys: int) -> bool:
    """Train `linker`'s model, whose database is `db_api`'s, on its contributors (spec §6.3);
    whether u and m were estimated.

    The probability two random keys match is always estimated, by counting deterministic
    matches. u is estimated by random sampling and m by expectation maximisation on each
    blocking rule only when there are at least `min_training_keys` keys: on fewer, a random
    sample measures how often the sample's few surnames collide, not the population's, and EM
    takes a household for a person. The model then keeps its priors for both.

    Each EM session's pairs are dropped as soon as the session ends (`TRAINING_SCRATCH`), so the
    working file holds one session's at a time, not all three.
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
        drop_scratch(db_api, TRAINING_SCRATCH)
    return True


def live_version(store: R2) -> str | None:
    """The live model: the newest model saved in R2 (`paths.resolution_model`) whose run
    finished, so also wrote its record (`paths.resolution_run`); None if there is none.

    Versions are `build_id`s, so the newest is the most recently trained. A run saves its model
    right after training and writes its record last (NEU-2325), so a run that stopped part way
    leaves a model that is not live: the donor_ids in place were not assigned with it. This is
    the model `validate` scores and `load` reports.
    """
    finished = {
        key.removeprefix(paths.RUN_PREFIX).removesuffix(".json")
        for key in store.list_keys(paths.RUN_PREFIX)
    }
    versions = [
        version
        for key in store.list_keys(paths.MODEL_PREFIX)
        if (version := paths.model_version_of(key)) is not None and version in finished
    ]
    return max(versions) if versions else None
