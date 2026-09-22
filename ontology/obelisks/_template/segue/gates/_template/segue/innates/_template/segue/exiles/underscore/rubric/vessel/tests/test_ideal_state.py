#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from hypothesis import (
    given,
    settings,
    strategies as st,
)


source = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/underscore/rubric/vessel/source/ideal_state.py"
)

spec = (
    importlib.util
    .spec_from_file_location(
        "savant_underscore_vessel_ideal_state",
        source,
    )
)

if (
    spec is None
    or spec.loader is None
):
    raise RuntimeError(
        "unable to load ideal state engine"
    )

module = (
    importlib.util
    .module_from_spec(
        spec
    )
)

sys.modules[
    spec.name
] = module

spec.loader.exec_module(
    module
)


text_strategy = (
    st.text(
        alphabet=(
            st.characters(
                whitelist_categories=(
                    "Ll",
                    "Lu",
                    "Nd",
                    "Zs",
                )
            )
        ),
        min_size=3,
        max_size=160,
    )
    .filter(
        lambda value: bool(
            value.strip()
        )
    )
)


@settings(
    max_examples=60,
    deadline=None,
)
@given(
    st.lists(
        text_strategy,
        min_size=2,
        max_size=10,
        unique=True,
    )
)
def test_deterministic_analysis(
    texts,
):
    payload = {
        "subject": (
            "property based "
            "divergence test"
        ),
        "candidates": [
            {
                "instance_id": (
                    f"candidate_{index}"
                ),
                "text": text,
            }
            for index, text
            in enumerate(
                texts
            )
        ],
        "baselines": [],
        "cliches": [],
        "constraints": {
            "required": [],
            "forbidden": [],
        },
    }

    engine = (
        module.IdealStateEngine(
            archive_size=16,
            experiment_limit=8,
            minimum_elites=1,
        )
    )

    first = engine.analyze(
        payload
    )

    second = engine.analyze(
        payload
    )

    assert (
        first["fingerprint"]
        == second["fingerprint"]
    )

    assert (
        first["authority_effect"]
        == "none"
    )

    assert (
        first["candidate_count"]
        == len(texts)
    )

    for candidate in (
        first[
            "ranked_candidates"
        ]
    ):
        for value in (
            candidate[
                "metrics"
            ].values()
        ):
            assert (
                0.0
                <= float(value)
                <= 1.0
            )


@settings(
    max_examples=40,
    deadline=None,
)
@given(
    required=st.lists(
        text_strategy,
        max_size=4,
        unique=True,
    ),
    forbidden=st.lists(
        text_strategy,
        max_size=4,
        unique=True,
    ),
)
def test_constraint_score_bounded(
    required,
    forbidden,
):
    score, detail = (
        module.constraint_integrity(
            "candidate text",
            {
                "required": required,
                "forbidden": forbidden,
            },
        )
    )

    assert (
        0.0
        <= score
        <= 1.0
    )

    assert isinstance(
        detail[
            "required_hits"
        ],
        list,
    )

    assert isinstance(
        detail[
            "required_misses"
        ],
        list,
    )

    assert isinstance(
        detail[
            "forbidden_hits"
        ],
        list,
    )
