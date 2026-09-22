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

production_path = (
    source_root
    / "production_pipeline.py"
)

schema_version = (
    "savant.underscore."
    "production-stable.v1"
)

authority_effect = "none"


volatile_keys = frozenset(
    {
        "run_id",
        "vessel_run_id",
        "duration_ms",
        "started_at",
        "ended_at",
        "created_at",
        "updated_at",
        "timestamp",
        "observed_at",
        "recorded_at",
    }
)


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


production = load_module(
    "savant_underscore_production_pipeline",
    production_path,
)


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        output = {}

        for key in sorted(
            value
        ):
            if key in volatile_keys:
                continue

            if key == "fingerprint":
                continue

            output[
                key
            ] = (
                deterministic_projection(
                    value[
                        key
                    ]
                )
            )

        return output

    if isinstance(
        value,
        list,
    ):
        return [
            deterministic_projection(
                item
            )
            for item in value
        ]

    if isinstance(
        value,
        tuple,
    ):
        return [
            deterministic_projection(
                item
            )
            for item in value
        ]

    return value


def deterministic_fingerprint(
    result: dict[str, Any],
) -> str:
    return digest(
        deterministic_projection(
            result
        )
    )


def volatile_projection(
    result: dict[str, Any],
) -> dict[str, Any]:
    receipts = []

    recursive = result.get(
        "recursion",
        {},
    )

    if isinstance(
        recursive,
        dict,
    ):
        generations = recursive.get(
            "generations",
            [],
        )

        if isinstance(
            generations,
            list,
        ):
            for generation in generations:
                if not isinstance(
                    generation,
                    dict,
                ):
                    continue

                stages = generation.get(
                    "stages",
                    {},
                )

                if not isinstance(
                    stages,
                    dict,
                ):
                    continue

                vessel = stages.get(
                    "vessel",
                    {},
                )

                if not isinstance(
                    vessel,
                    dict,
                ):
                    continue

                run_id = vessel.get(
                    "run_id"
                )

                if run_id:
                    receipts.append(
                        {
                            "generation": (
                                generation.get(
                                    "generation"
                                )
                            ),
                            "branch_id": (
                                generation.get(
                                    "branch_id"
                                )
                            ),
                            "vessel_run_id": (
                                run_id
                            ),
                        }
                    )

    return {
        "operational_receipts": (
            receipts
        ),
        "receipt_count": len(
            receipts
        ),
    }


class StableProductionPipeline:
    def __init__(
        self,
        pipeline: Any,
    ) -> None:
        self.pipeline = pipeline

    def execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        result = (
            self.pipeline.execute(
                payload
            )
        )

        if (
            result.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "production pipeline "
                "attempted authority effect"
            )

        original_fingerprint = (
            result.get(
                "fingerprint"
            )
        )

        semantic_projection = (
            deterministic_projection(
                result
            )
        )

        semantic_fingerprint = (
            digest(
                semantic_projection
            )
        )

        result[
            "execution_projection"
        ] = (
            volatile_projection(
                result
            )
        )

        result[
            "fingerprints"
        ] = {
            "semantic": (
                semantic_fingerprint
            ),
            "legacy_execution_sensitive": (
                original_fingerprint
            ),
        }

        result[
            "fingerprint"
        ] = (
            semantic_fingerprint
        )

        result[
            "determinism"
        ] = {
            "semantic_identity_excludes_operational_receipts": (
                True
            ),
            "operational_receipts_preserved": (
                True
            ),
            "volatile_keys": sorted(
                volatile_keys
            ),
            "semantic_projection_schema": (
                "savant.underscore."
                "semantic-projection.v1"
            ),
        }

        result[
            "invariants"
        ] = {
            **result.get(
                "invariants",
                {},
            ),
            "semantic_fingerprint_deterministic": (
                True
            ),
            "execution_identity_not_semantic_identity": (
                True
            ),
            "vessel_run_receipts_preserved": (
                True
            ),
        }

        return result


def build_pipeline_from_args(
    args: argparse.Namespace,
) -> StableProductionPipeline:
    realizer = (
        production
        .recursive_module
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

    pipeline = (
        production.ProductionPipeline(
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
    )

    return StableProductionPipeline(
        pipeline
    )


def fixture_pipeline(
    *,
    recurse_unresolved: bool,
) -> StableProductionPipeline:
    base = (
        production
        .build_fixture_pipeline(
            recurse_unresolved=(
                recurse_unresolved
            )
        )
    )

    return StableProductionPipeline(
        base
    )


def self_check() -> dict[str, Any]:
    pipeline = (
        fixture_pipeline(
            recurse_unresolved=False
        )
    )

    payload = (
        production.fixture_payload()
    )

    first = pipeline.execute(
        payload
    )

    second = pipeline.execute(
        payload
    )

    first_semantic = (
        first[
            "fingerprints"
        ][
            "semantic"
        ]
    )

    second_semantic = (
        second[
            "fingerprints"
        ][
            "semantic"
        ]
    )

    if (
        first_semantic
        != second_semantic
    ):
        raise RuntimeError(
            "semantic determinism failed"
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

    champion = (
        first[
            "selection"
        ].get(
            "champion"
        )
    )

    if champion is None:
        raise RuntimeError(
            "champion projection failed"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "semantic_determinism": (
            "passed"
        ),
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
        "semantic_fingerprint": (
            first_semantic
        ),
        "execution_receipt_count": (
            first[
                "execution_projection"
            ][
                "receipt_count"
            ]
        ),
    }


def branch_check() -> dict[str, Any]:
    pipeline = (
        fixture_pipeline(
            recurse_unresolved=True
        )
    )

    result = pipeline.execute(
        production.fixture_payload()
    )

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

    recursion = result.get(
        "recursion",
        {},
    )

    if not isinstance(
        recursion,
        dict,
    ):
        recursion = {}

    recursion_segues = recursion.get(
        "segues",
        [],
    )

    if not isinstance(
        recursion_segues,
        list,
    ):
        recursion_segues = []

    if generation_count < 2:
        raise RuntimeError(
            "multi-generation branch "
            "was not exercised"
        )

    if not recursion_segues:
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
            len(
                recursion_segues
            )
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
        "semantic_fingerprint": (
            result[
                "fingerprints"
            ][
                "semantic"
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-production"
        ),
        description=(
            "stable semantic production "
            "composition for underscore "
            "and vessel"
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
        pipeline = (
            build_pipeline_from_args(
                args
            )
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
