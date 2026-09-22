#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from primitives import require_object
from primitives import load_json
from primitives import load_module_production as load_module


runtime_root = Path(
    "/root/savant-runtime"
)

underscore_root = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "underscore"
)

source_root = (
    underscore_root
    / "rubric"
    / "vessel"
    / "source"
)

recursive_path = (
    source_root
    / "recursive_pipeline.py"
)

ideal_state_path = (
    source_root
    / "ideal_state.py"
)

negative_knowledge_path = (
    source_root
    / "negative_knowledge.py"
)

schema_version = (
    "savant.underscore."
    "production-pipeline.v1"
)

authority_effect = "none"


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


recursive_module = load_module(
    "savant_underscore_recursive",
    recursive_path,
)

ideal_module = load_module(
    "savant_underscore_ideal_state",
    ideal_state_path,
)

negative_module = load_module(
    "savant_underscore_negative_knowledge",
    negative_knowledge_path,
)


def candidate_from_record(
    record: Any,
) -> dict[str, Any] | None:
    if not isinstance(
        record,
        dict,
    ):
        return None

    candidate = record.get(
        "candidate"
    )

    if not isinstance(
        candidate,
        dict,
    ):
        return None

    text = str(
        candidate.get(
            "text",
            "",
        )
    ).strip()

    if not text:
        return None

    return candidate


def candidate_identity(
    candidate: dict[str, Any],
) -> str:
    explicit = str(
        candidate.get(
            "instance_id",
            candidate.get(
                "candidate_id",
                "",
            ),
        )
    ).strip()

    if explicit:
        return explicit

    return (
        "candidate_"
        + digest(
            {
                "text": (
                    candidate.get(
                        "text",
                        ""
                    )
                ),
                "lineage": (
                    candidate.get(
                        "lineage",
                        [],
                    )
                ),
            }
        )[:24]
    )


def deduplicate_candidates(
    candidates: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    by_identity = {}
    seen_text = set()

    for candidate in candidates:
        identity = candidate_identity(
            candidate
        )

        normalized_text = " ".join(
            str(
                candidate.get(
                    "text",
                    "",
                )
            )
            .casefold()
            .split()
        )

        if not normalized_text:
            continue

        text_key = hashlib.sha256(
            normalized_text.encode(
                "utf-8"
            )
        ).hexdigest()

        if text_key in seen_text:
            continue

        seen_text.add(
            text_key
        )

        by_identity[
            identity
        ] = {
            **candidate,
            "instance_id": identity,
        }

    return [
        by_identity[
            key
        ]
        for key
        in sorted(
            by_identity
        )
    ]


def final_candidates(
    recursive_result: dict[
        str,
        Any,
    ],
) -> list[
    dict[str, Any]
]:
    frontier = require_object(
        recursive_result.get(
            "final_frontier",
            {},
        ),
        "final_frontier",
    )

    candidates = []

    for frontier_name in (
        "surviving",
        "mutation_terminal",
        "unresolved_terminal",
        "rejected",
        "unknown",
    ):
        records = frontier.get(
            frontier_name,
            [],
        )

        if not isinstance(
            records,
            list,
        ):
            continue

        for record in records:
            candidate = (
                candidate_from_record(
                    record
                )
            )

            if candidate is None:
                continue

            candidates.append(
                {
                    **candidate,
                    "frontier": (
                        frontier_name
                    ),
                }
            )

    return deduplicate_candidates(
        candidates
    )


def elite_projection(
    ideal_result: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    ranked = ideal_result.get(
        "ranked_candidates",
        [],
    )

    if not isinstance(
        ranked,
        list,
    ):
        ranked = []

    pareto_ids = set(
        str(
            value
        )
        for value
        in ideal_result.get(
            "pareto_frontier",
            [],
        )
    )

    archive = (
        ideal_result.get(
            "quality_diversity",
            {},
        )
    )

    if not isinstance(
        archive,
        dict,
    ):
        archive = {}

    archive_rows = archive.get(
        "archive",
        [],
    )

    if not isinstance(
        archive_rows,
        list,
    ):
        archive_rows = []

    archive_ids = {
        str(
            row.get(
                "candidate_id",
                "",
            )
        )
        for row
        in archive_rows
        if isinstance(
            row,
            dict,
        )
    }

    candidates = {}

    for record in ranked:
        if not isinstance(
            record,
            dict,
        ):
            continue

        candidate_id = str(
            record.get(
                "candidate_id",
                "",
            )
        )

        if candidate_id:
            candidates[
                candidate_id
            ] = record

    intersection = sorted(
        pareto_ids
        & archive_ids
    )

    if intersection:
        preferred_pool = [
            candidates[
                candidate_id
            ]
            for candidate_id
            in intersection
            if candidate_id
            in candidates
        ]

    elif pareto_ids:
        preferred_pool = [
            candidates[
                candidate_id
            ]
            for candidate_id
            in sorted(
                pareto_ids
            )
            if candidate_id
            in candidates
        ]

    else:
        preferred_pool = list(
            ranked
        )

    preferred_pool.sort(
        key=lambda record: (
            -float(
                record.get(
                    "metrics",
                    {},
                ).get(
                    "objective",
                    0.0,
                )
            ),
            str(
                record.get(
                    "candidate_id",
                    "",
                )
            ),
        )
    )

    champion = (
        preferred_pool[0]
        if preferred_pool
        else None
    )

    elites = (
        preferred_pool[:8]
    )

    return {
        "champion": champion,
        "elites": elites,
        "selection_basis": (
            "pareto_and_quality_diversity"
            if intersection
            else (
                "pareto"
                if pareto_ids
                else "ranked_objective"
            )
        ),
        "authoritative": False,
        "authority_effect": "none",
    }


class ProductionPipeline:
    def __init__(
        self,
        *,
        realizer: Any,
        max_generations: int,
        recurse_unresolved: bool,
        candidate_count: int,
        cliche_threshold: float,
        similarity_threshold: float,
        frontier_size: int,
        mmr_lambda: float,
        archive_size: int,
        experiment_limit: int,
        collapse_similarity: float,
        minimum_elites: int,
    ) -> None:
        self.recursive = (
            recursive_module
            .RecursiveUnderscore(
                realizer=realizer,
                max_generations=(
                    max_generations
                ),
                recurse_unresolved=(
                    recurse_unresolved
                ),
                candidate_count=(
                    candidate_count
                ),
                cliche_threshold=(
                    cliche_threshold
                ),
                similarity_threshold=(
                    similarity_threshold
                ),
                frontier_size=(
                    frontier_size
                ),
                mmr_lambda=(
                    mmr_lambda
                ),
            )
        )

        self.ideal = (
            ideal_module
            .IdealStateEngine(
                archive_size=(
                    archive_size
                ),
                experiment_limit=(
                    experiment_limit
                ),
                collapse_similarity=(
                    collapse_similarity
                ),
                minimum_elites=(
                    minimum_elites
                ),
            )
        )

        self.negative = (
            negative_module
            .NegativeKnowledgeCompiler()
        )

    def execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload = require_object(
            payload,
            "input",
        )

        subject = str(
            payload.get(
                "subject",
                "",
            )
        ).strip()

        if not subject:
            raise ValueError(
                "subject is required"
            )

        prior_negative = (
            payload.get(
                "negative_knowledge",
                {},
            )
        )

        if not isinstance(
            prior_negative,
            dict,
        ):
            prior_negative = {}

        recursive_result = (
            self.recursive.execute(
                payload
            )
        )

        if (
            recursive_result.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "recursive stage "
                "attempted authority effect"
            )

        current_negative = (
            self.negative.compile(
                recursive_result
            )
        )

        if (
            current_negative.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "negative knowledge stage "
                "attempted authority effect"
            )

        candidates = final_candidates(
            recursive_result
        )

        if not candidates:
            raise RuntimeError(
                "recursive pipeline "
                "produced no candidate "
                "projection for idealization"
            )

        ideal_payload = {
            "subject": subject,
            "candidates": (
                candidates
            ),
            "baselines": (
                payload.get(
                    "baselines",
                    [],
                )
            ),
            "cliches": (
                payload.get(
                    "cliches",
                    [],
                )
            ),
            "constraints": (
                payload.get(
                    "constraints",
                    {},
                )
            ),
            "negative_knowledge": (
                prior_negative
            ),
        }

        ideal_result = (
            self.ideal.analyze(
                ideal_payload
            )
        )

        if (
            ideal_result.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "ideal state stage "
                "attempted authority effect"
            )

        selection = (
            elite_projection(
                ideal_result
            )
        )

        scrybe_request = (
            ideal_result.get(
                "scrybe_recall_query",
                {},
            )
        )

        if not isinstance(
            scrybe_request,
            dict,
        ):
            scrybe_request = {}

        if scrybe_request.get(
            "direct_write_requested"
        ):
            raise RuntimeError(
                "direct scrybe write "
                "is forbidden"
            )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "authority_effect": (
                authority_effect
            ),
            "subject": subject,
            "stages": {
                "recursive": {
                    "schema": (
                        recursive_result.get(
                            "schema"
                        )
                    ),
                    "generation_count": (
                        recursive_result.get(
                            "generation_count"
                        )
                    ),
                    "branch_count": (
                        recursive_result.get(
                            "branch_count"
                        )
                    ),
                    "fingerprint": (
                        recursive_result.get(
                            "fingerprint"
                        )
                    ),
                },
                "ideal_state": {
                    "schema": (
                        ideal_result.get(
                            "schema"
                        )
                    ),
                    "enhancement_count": (
                        ideal_result.get(
                            "enhancement_count"
                        )
                    ),
                    "candidate_count": (
                        ideal_result.get(
                            "candidate_count"
                        )
                    ),
                    "pareto_count": len(
                        ideal_result.get(
                            "pareto_frontier",
                            [],
                        )
                    ),
                    "archive_cells": (
                        ideal_result.get(
                            "quality_diversity",
                            {},
                        ).get(
                            "occupied_cells"
                        )
                    ),
                    "fingerprint": (
                        ideal_result.get(
                            "fingerprint"
                        )
                    ),
                },
                "negative_knowledge": {
                    "schema": (
                        current_negative.get(
                            "schema"
                        )
                    ),
                    "packet_count": (
                        current_negative.get(
                            "packet_count"
                        )
                    ),
                    "fingerprint": (
                        current_negative.get(
                            "fingerprint"
                        )
                    ),
                },
            },
            "selection": (
                selection
            ),
            "quality_diversity": (
                ideal_result.get(
                    "quality_diversity",
                    {},
                )
            ),
            "pareto_frontier": (
                ideal_result.get(
                    "pareto_frontier",
                    [],
                )
            ),
            "experiments": (
                ideal_result.get(
                    "experiments",
                    [],
                )
            ),
            "stopping_policy": (
                ideal_result.get(
                    "stopping_policy",
                    {},
                )
            ),
            "contradictions": (
                ideal_result.get(
                    "contradictions",
                    [],
                )
            ),
            "assumption_graph": (
                ideal_result.get(
                    "assumption_graph",
                    {},
                )
            ),
            "lineage_graph": (
                ideal_result.get(
                    "lineage_graph",
                    {},
                )
            ),
            "novelty_archive": (
                ideal_result.get(
                    "novelty_archive",
                    [],
                )
            ),
            "negative_knowledge": {
                "prior": (
                    prior_negative
                ),
                "current_projection": (
                    current_negative
                ),
            },
            "scrybe_recall_request": (
                scrybe_request
            ),
            "recursion": {
                "generations": (
                    recursive_result.get(
                        "generations",
                        [],
                    )
                ),
                "segues": (
                    recursive_result.get(
                        "recursion_segues",
                        [],
                    )
                ),
                "final_frontier": (
                    recursive_result.get(
                        "final_frontier",
                        {},
                    )
                ),
            },
            "invariants": {
                "projection_only": True,
                "authority_effect_none": True,
                "no_canon_admission": True,
                "no_direct_scrybe_write": True,
                "no_coda_mutation": True,
                "no_evidence_admission": True,
                "no_provider_ownership_transfer": True,
                "novelty_is_not_authority": True,
                "quality_is_not_authority": True,
                "selection_is_not_authority": True,
                "negative_knowledge_is_not_fact": True,
                "candidate_lineage_preserved": True,
                "bounded_recursion": True,
                "quality_diversity_active": True,
                "anti_goodhart_active": True,
            },
        }

        result[
            "fingerprint"
        ] = digest(
            {
                "schema": (
                    schema_version
                ),
                "subject": subject,
                "recursive": (
                    result[
                        "stages"
                    ][
                        "recursive"
                    ]
                ),
                "ideal_state": (
                    result[
                        "stages"
                    ][
                        "ideal_state"
                    ]
                ),
                "negative_knowledge": (
                    result[
                        "stages"
                    ][
                        "negative_knowledge"
                    ]
                ),
                "selection": (
                    selection
                ),
                "stopping_policy": (
                    result[
                        "stopping_policy"
                    ]
                ),
            }
        )

        return result


def fixture_payload() -> dict[str, Any]:
    return {
        "subject": (
            "produce an ending that "
            "subverts conventional victory"
        ),
        "context": (
            "The ending must follow "
            "from already-visible facts."
        ),
        "candidate_count": 8,
        "baselines": [
            (
                "the protagonist defeats "
                "the antagonist and receives "
                "the expected reward"
            )
        ],
        "cliches": [
            "the chosen one",
            "last-second rescue",
            "secret identity reveal",
            "everyone celebrates",
        ],
        "constraints": {
            "required": [],
            "forbidden": [],
        },
        "negative_knowledge": {
            "schema": (
                "savant.underscore.vessel."
                "negative-knowledge.v1"
            ),
            "authority_effect": "none",
            "mechanism_counts": {
                "cliche_pressure": 1,
            },
            "packets": [
                {
                    "evidence": {
                        "text": (
                            "the winner is "
                            "secretly someone else"
                        )
                    }
                }
            ],
        },
    }


def build_fixture_pipeline(
    *,
    recurse_unresolved: bool,
) -> ProductionPipeline:
    return ProductionPipeline(
        realizer=(
            recursive_module
            .pipeline_module
            .realization
            .FixtureRealizer()
        ),
        max_generations=2,
        recurse_unresolved=(
            recurse_unresolved
        ),
        candidate_count=8,
        cliche_threshold=0.68,
        similarity_threshold=0.74,
        frontier_size=7,
        mmr_lambda=0.68,
        archive_size=18,
        experiment_limit=8,
        collapse_similarity=0.86,
        minimum_elites=2,
    )


def self_check() -> dict[str, Any]:
    pipeline = (
        build_fixture_pipeline(
            recurse_unresolved=False
        )
    )

    payload = fixture_payload()

    first = pipeline.execute(
        payload
    )

    second = pipeline.execute(
        payload
    )

    if (
        first[
            "fingerprint"
        ]
        != second[
            "fingerprint"
        ]
    ):
        raise RuntimeError(
            "production determinism failed"
        )

    if (
        first[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "authority invariant failed"
        )

    ideal_stage = (
        first[
            "stages"
        ][
            "ideal_state"
        ]
    )

    if int(
        ideal_stage.get(
            "enhancement_count",
            0,
        )
    ) < 28:
        raise RuntimeError(
            "ideal state integration failed"
        )

    if int(
        ideal_stage.get(
            "candidate_count",
            0,
        )
    ) <= 0:
        raise RuntimeError(
            "candidate projection failed"
        )

    if (
        first[
            "scrybe_recall_request"
        ].get(
            "direct_write_requested"
        )
    ):
        raise RuntimeError(
            "scrybe ownership violated"
        )

    if (
        first[
            "selection"
        ][
            "champion"
        ]
        is None
    ):
        raise RuntimeError(
            "non-authoritative "
            "champion projection failed"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "enhancement_count": (
            ideal_stage[
                "enhancement_count"
            ]
        ),
        "candidate_count": (
            ideal_stage[
                "candidate_count"
            ]
        ),
        "pareto_count": (
            ideal_stage[
                "pareto_count"
            ]
        ),
        "archive_cells": (
            ideal_stage[
                "archive_cells"
            ]
        ),
        "negative_knowledge_packets": (
            first[
                "stages"
            ][
                "negative_knowledge"
            ][
                "packet_count"
            ]
        ),
        "selection_basis": (
            first[
                "selection"
            ][
                "selection_basis"
            ]
        ),
        "fingerprint": (
            first[
                "fingerprint"
            ]
        ),
    }


def branch_check() -> dict[str, Any]:
    pipeline = (
        build_fixture_pipeline(
            recurse_unresolved=True
        )
    )

    result = pipeline.execute(
        fixture_payload()
    )

    recursion = result[
        "recursion"
    ]

    generation_count = int(
        result[
            "stages"
        ][
            "recursive"
        ].get(
            "generation_count",
            0,
        )
    )

    segue_count = len(
        recursion.get(
            "segues",
            [],
        )
    )

    if generation_count < 2:
        raise RuntimeError(
            "multi-generation branch "
            "was not exercised"
        )

    if segue_count < 1:
        raise RuntimeError(
            "recursive segue "
            "was not exercised"
        )

    if (
        result[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "authority invariant failed"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "branch_check": "passed",
        "generation_count": (
            generation_count
        ),
        "branch_count": (
            result[
                "stages"
            ][
                "recursive"
            ][
                "branch_count"
            ]
        ),
        "recursion_segue_count": (
            segue_count
        ),
        "ideal_candidate_count": (
            result[
                "stages"
            ][
                "ideal_state"
            ][
                "candidate_count"
            ]
        ),
        "fingerprint": (
            result[
                "fingerprint"
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-production"
        ),
        description=(
            "production composition of "
            "underscore divergence, vessel, "
            "bounded recursion, quality "
            "diversity, falsification, and "
            "negative knowledge projection"
        ),
    )

    parser.add_argument(
        "--adapter",
        choices=(
            "fixture",
            "recorded",
            "external-command",
        ),
        default="fixture",
    )

    parser.add_argument(
        "--records",
    )

    parser.add_argument(
        "--command",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
    )

    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=262144,
    )

    parser.add_argument(
        "--max-generations",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--candidate-count",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--recurse-unresolved",
        action=(
            argparse.BooleanOptionalAction
        ),
        default=True,
    )

    parser.add_argument(
        "--cliche-threshold",
        type=float,
        default=0.68,
    )

    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.74,
    )

    parser.add_argument(
        "--frontier-size",
        type=int,
        default=7,
    )

    parser.add_argument(
        "--mmr-lambda",
        type=float,
        default=0.68,
    )

    parser.add_argument(
        "--archive-size",
        type=int,
        default=18,
    )

    parser.add_argument(
        "--experiment-limit",
        type=int,
        default=12,
    )

    parser.add_argument(
        "--collapse-similarity",
        type=float,
        default=0.86,
    )

    parser.add_argument(
        "--minimum-elites",
        type=int,
        default=4,
    )

    commands = (
        parser.add_subparsers(
            dest="action",
            required=True,
        )
    )

    execute = commands.add_parser(
        "execute"
    )

    execute.add_argument(
        "--input",
        required=True,
    )

    commands.add_parser(
        "self-check"
    )

    commands.add_parser(
        "branch-check"
    )

    return parser


def main() -> int:
    args = (
        build_parser()
        .parse_args()
    )

    if args.action == "self-check":
        result = self_check()

    elif args.action == "branch-check":
        result = branch_check()

    elif args.action == "execute":
        realizer = (
            recursive_module
            .pipeline_module
            .build_realizer(
                args.adapter,
                records=(
                    args.records
                ),
                command=(
                    args.command
                ),
                timeout=(
                    args.timeout
                ),
                max_output_bytes=(
                    args.max_output_bytes
                ),
            )
        )

        pipeline = ProductionPipeline(
            realizer=realizer,
            max_generations=(
                args.max_generations
            ),
            recurse_unresolved=(
                args.recurse_unresolved
            ),
            candidate_count=(
                args.candidate_count
            ),
            cliche_threshold=(
                args.cliche_threshold
            ),
            similarity_threshold=(
                args.similarity_threshold
            ),
            frontier_size=(
                args.frontier_size
            ),
            mmr_lambda=(
                args.mmr_lambda
            ),
            archive_size=(
                args.archive_size
            ),
            experiment_limit=(
                args.experiment_limit
            ),
            collapse_similarity=(
                args.collapse_similarity
            ),
            minimum_elites=(
                args.minimum_elites
            ),
        )

        result = pipeline.execute(
            load_json(
                args.input
            )
        )

    else:
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
