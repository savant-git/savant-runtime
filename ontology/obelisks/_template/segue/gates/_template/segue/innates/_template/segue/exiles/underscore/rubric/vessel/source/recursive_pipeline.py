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
from primitives import bind_stable_id
from primitives import load_json
from primitives import load_module


runtime_root = Path("/root/savant-runtime")

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

pipeline_path = (
    source_root
    / "underscore_pipeline.py"
)

schema_version = (
    "savant.underscore.recursive-pipeline.v1"
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
        ).encode("utf-8")
    ).hexdigest()


stable_id = bind_stable_id(digest)

def normalize_text(
    value: Any,
) -> str:
    return " ".join(
        str(
            value
            or ""
        ).casefold().split()
    )


def semantic_key(
    text: Any,
) -> str:
    return hashlib.sha256(
        normalize_text(
            text
        ).encode("utf-8")
    ).hexdigest()


pipeline_module = load_module(
    "savant_underscore_pipeline",
    pipeline_path,
)


def segue_classification(
    segue: dict[str, Any],
) -> str:
    segue_type = str(
        segue.get(
            "segue_type",
            "",
        )
    ).casefold()

    for value in (
        "surviving",
        "mutation",
        "unresolved",
        "rejected",
    ):
        if value in segue_type:
            return value

    payload = segue.get(
        "payload",
        {},
    )

    if isinstance(
        payload,
        dict,
    ):
        for key in (
            "classification",
            "frontier",
            "status",
            "destination",
            "outcome",
        ):
            value = str(
                payload.get(
                    key,
                    "",
                )
            ).casefold()

            if value in (
                "surviving",
                "mutation",
                "unresolved",
                "rejected",
            ):
                return value

    return "unknown"


def source_id_from_segue(
    segue: dict[str, Any],
) -> str:
    for key in (
        "source_instance_id",
        "candidate_id",
        "instance_id",
    ):
        value = str(
            segue.get(
                key,
                "",
            )
        ).strip()

        if value:
            return value

    payload = segue.get(
        "payload",
        {},
    )

    if isinstance(
        payload,
        dict,
    ):
        for key in (
            "source_instance_id",
            "candidate_id",
            "instance_id",
            "realized_instance_id",
        ):
            value = str(
                payload.get(
                    key,
                    "",
                )
            ).strip()

            if value:
                return value

    return ""


class RecursiveUnderscore:
    def __init__(
        self,
        *,
        realizer: Any,
        max_generations: int = 3,
        recurse_unresolved: bool = True,
        candidate_count: int = 8,
        cliche_threshold: float = 0.68,
        similarity_threshold: float = 0.74,
        frontier_size: int = 7,
        mmr_lambda: float = 0.68,
    ) -> None:
        self.max_generations = max(
            1,
            min(
                int(
                    max_generations
                ),
                8,
            ),
        )

        self.recurse_unresolved = bool(
            recurse_unresolved
        )

        self.candidate_count = max(
            4,
            min(
                int(
                    candidate_count
                ),
                32,
            ),
        )

        self.pipeline = (
            pipeline_module.UnderscorePipeline(
                realizer=realizer,
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

    @staticmethod
    def egress(
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        segues = result.get(
            "segues",
            {},
        )

        if not isinstance(
            segues,
            dict,
        ):
            return []

        values = segues.get(
            "vessel_egress",
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            return []

        return [
            item
            for item in values
            if isinstance(
                item,
                dict,
            )
        ]

    @staticmethod
    def candidate_index(
        result: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        instances = result.get(
            "_realized_instances",
            [],
        )

        if not isinstance(
            instances,
            list,
        ):
            return {}

        output = {}

        for instance in instances:
            if not isinstance(
                instance,
                dict,
            ):
                continue

            instance_id = str(
                instance.get(
                    "instance_id",
                    "",
                )
            ).strip()

            if instance_id:
                output[
                    instance_id
                ] = instance

        return output

    def classify(
        self,
        result: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        index = self.candidate_index(
            result
        )

        classified = {
            "surviving": [],
            "mutation": [],
            "unresolved": [],
            "rejected": [],
            "unknown": [],
        }

        for segue in self.egress(
            result
        ):
            classification = (
                segue_classification(
                    segue
                )
            )

            source_id = (
                source_id_from_segue(
                    segue
                )
            )

            record = {
                "classification": (
                    classification
                ),
                "source_instance_id": (
                    source_id
                ),
                "candidate": (
                    index.get(
                        source_id
                    )
                ),
                "segue": segue,
            }

            classified.setdefault(
                classification,
                classified[
                    "unknown"
                ],
            ).append(
                record
            )

        return classified

    def branch_payload(
        self,
        root_payload: dict[str, Any],
        seed: dict[str, Any],
        *,
        generation: int,
    ) -> dict[str, Any]:
        candidate = seed.get(
            "candidate"
        )

        if not isinstance(
            candidate,
            dict,
        ):
            raise ValueError(
                "recursive seed has no "
                "realized candidate"
            )

        text = str(
            candidate.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            raise ValueError(
                "recursive seed has no text"
            )

        classification = str(
            seed.get(
                "classification",
                "unresolved",
            )
        )

        previous_context = str(
            root_payload.get(
                "context",
                "",
            )
        ).strip()

        recursive_context = (
            "Recursive underscore generation "
            f"{generation}. Vessel classified "
            "the previous candidate as "
            f"{classification}. Do not merely "
            "paraphrase it. Change a governing "
            "assumption, mechanism, causal "
            "structure, information structure, "
            "constraint interaction, category, "
            "scale, agency, or payoff while "
            "preserving all hard constraints."
        )

        if previous_context:
            recursive_context = (
                previous_context
                + "\n\n"
                + recursive_context
            )

        baselines = (
            root_payload.get(
                "baselines",
                [],
            )
        )

        if not isinstance(
            baselines,
            list,
        ):
            baselines = []

        baselines = [
            str(
                item
            )
            for item in baselines
        ]

        baselines.append(
            text
        )

        lineage = candidate.get(
            "lineage",
            [],
        )

        if not isinstance(
            lineage,
            list,
        ):
            lineage = []

        lineage = [
            str(
                item
            )
            for item in lineage
        ]

        source_instance_id = str(
            candidate.get(
                "instance_id",
                "",
            )
        ).strip()

        if source_instance_id:
            lineage.append(
                source_instance_id
            )

        return {
            "subject": (
                root_payload.get(
                    "subject",
                    "",
                )
            ),
            "context": (
                recursive_context
            ),
            "candidate_count": (
                self.candidate_count
            ),
            "baselines": (
                baselines
            ),
            "cliches": (
                root_payload.get(
                    "cliches",
                    [],
                )
            ),
            "constraints": (
                root_payload.get(
                    "constraints",
                    {},
                )
            ),
            "recursive": {
                "generation": generation,
                "source_instance_id": (
                    source_instance_id
                ),
                "source_classification": (
                    classification
                ),
                "lineage": lineage,
            },
        }

    def execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        root_payload = require_object(
            payload,
            "input",
        )

        subject = str(
            root_payload.get(
                "subject",
                "",
            )
        ).strip()

        if not subject:
            raise ValueError(
                "subject is required"
            )

        initial_payload = dict(
            root_payload
        )

        initial_payload[
            "candidate_count"
        ] = int(
            root_payload.get(
                "candidate_count",
                self.candidate_count,
            )
        )

        queue = [
            {
                "generation": 0,
                "branch_id": stable_id(
                    "branch",
                    {
                        "subject": subject,
                        "generation": 0,
                    },
                ),
                "payload": (
                    initial_payload
                ),
                "parent_instance_id": (
                    None
                ),
                "parent_classification": (
                    None
                ),
            }
        ]

        generations = []
        survivors = []
        rejected = []
        terminal_mutation = []
        terminal_unresolved = []
        unknown = []
        recursion_segues = []

        seen_branches = set()
        seen_seed_texts = set()

        while queue:
            branch = queue.pop(0)

            branch_id = str(
                branch[
                    "branch_id"
                ]
            )

            if branch_id in (
                seen_branches
            ):
                continue

            seen_branches.add(
                branch_id
            )

            generation = int(
                branch[
                    "generation"
                ]
            )

            result = (
                self.pipeline.execute(
                    branch[
                        "payload"
                    ]
                )
            )

            if (
                result.get(
                    "authority_effect"
                )
                != "none"
            ):
                raise RuntimeError(
                    "recursive branch attempted "
                    "authority effect"
                )

            classified = (
                self.classify(
                    result
                )
            )

            generations.append(
                {
                    "generation": generation,
                    "branch_id": branch_id,
                    "parent_instance_id": (
                        branch.get(
                            "parent_instance_id"
                        )
                    ),
                    "parent_classification": (
                        branch.get(
                            "parent_classification"
                        )
                    ),
                    "counts": {
                        key: len(
                            value
                        )
                        for key, value
                        in classified.items()
                    },
                    "stages": (
                        result.get(
                            "stages",
                            {},
                        )
                    ),
                }
            )

            survivors.extend(
                classified[
                    "surviving"
                ]
            )

            rejected.extend(
                classified[
                    "rejected"
                ]
            )

            unknown.extend(
                classified[
                    "unknown"
                ]
            )

            recursive_seeds = list(
                classified[
                    "mutation"
                ]
            )

            if self.recurse_unresolved:
                recursive_seeds.extend(
                    classified[
                        "unresolved"
                    ]
                )

            else:
                terminal_unresolved.extend(
                    classified[
                        "unresolved"
                    ]
                )

            next_generation = (
                generation + 1
            )

            if (
                next_generation
                >= self.max_generations
            ):
                terminal_mutation.extend(
                    classified[
                        "mutation"
                    ]
                )

                if self.recurse_unresolved:
                    terminal_unresolved.extend(
                        classified[
                            "unresolved"
                        ]
                    )

                continue

            for seed in (
                recursive_seeds
            ):
                candidate = seed.get(
                    "candidate"
                )

                if not isinstance(
                    candidate,
                    dict,
                ):
                    if (
                        seed.get(
                            "classification"
                        )
                        == "mutation"
                    ):
                        terminal_mutation.append(
                            seed
                        )

                    else:
                        terminal_unresolved.append(
                            seed
                        )

                    continue

                text = str(
                    candidate.get(
                        "text",
                        "",
                    )
                ).strip()

                if not text:
                    continue

                key = semantic_key(
                    text
                )

                if key in (
                    seen_seed_texts
                ):
                    continue

                seen_seed_texts.add(
                    key
                )

                next_payload = (
                    self.branch_payload(
                        root_payload,
                        seed,
                        generation=(
                            next_generation
                        ),
                    )
                )

                source_instance_id = str(
                    candidate.get(
                        "instance_id",
                        "",
                    )
                ).strip()

                classification = str(
                    seed.get(
                        "classification",
                        "unresolved",
                    )
                )

                next_branch_id = (
                    stable_id(
                        "branch",
                        {
                            "source_instance_id": (
                                source_instance_id
                            ),
                            "classification": (
                                classification
                            ),
                            "generation": (
                                next_generation
                            ),
                            "payload": (
                                next_payload
                            ),
                        },
                    )
                )

                recursion_segue = {
                    "segue_id": stable_id(
                        "segue",
                        {
                            "type": (
                                "underscore.vessel."
                                "frontier_to_divergence"
                            ),
                            "source_instance_id": (
                                source_instance_id
                            ),
                            "classification": (
                                classification
                            ),
                            "generation": (
                                next_generation
                            ),
                            "branch_id": (
                                next_branch_id
                            ),
                        },
                    ),
                    "segue_type": (
                        "underscore.vessel."
                        "frontier_to_divergence"
                    ),
                    "owner": "underscore",
                    "source_instance_id": (
                        source_instance_id
                    ),
                    "target": (
                        "underscore.divergence"
                    ),
                    "authority_effect": (
                        "none"
                    ),
                    "payload": {
                        "classification": (
                            classification
                        ),
                        "generation": (
                            next_generation
                        ),
                        "branch_id": (
                            next_branch_id
                        ),
                    },
                }

                recursion_segues.append(
                    recursion_segue
                )

                queue.append(
                    {
                        "generation": (
                            next_generation
                        ),
                        "branch_id": (
                            next_branch_id
                        ),
                        "payload": (
                            next_payload
                        ),
                        "parent_instance_id": (
                            source_instance_id
                        ),
                        "parent_classification": (
                            classification
                        ),
                    }
                )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "authority_effect": (
                authority_effect
            ),
            "subject": subject,
            "configuration": {
                "max_generations": (
                    self.max_generations
                ),
                "recurse_unresolved": (
                    self.recurse_unresolved
                ),
                "candidate_count": (
                    self.candidate_count
                ),
            },
            "generation_count": len(
                {
                    item[
                        "generation"
                    ]
                    for item in generations
                }
            ),
            "branch_count": len(
                generations
            ),
            "generations": (
                generations
            ),
            "final_frontier": {
                "surviving": (
                    survivors
                ),
                "mutation_terminal": (
                    terminal_mutation
                ),
                "unresolved_terminal": (
                    terminal_unresolved
                ),
                "rejected": (
                    rejected
                ),
                "unknown": (
                    unknown
                ),
            },
            "recursion_segues": (
                recursion_segues
            ),
            "invariants": {
                "authority_effect_none": True,
                "bounded_recursion": True,
                "rejected_candidates_do_not_recurse": True,
                "surviving_candidates_do_not_recurse": True,
                "mutation_candidates_may_recurse": True,
                "unresolved_recursion_is_configurable": True,
                "duplicate_text_branches_suppressed": True,
                "generation_lineage_preserved": True,
                "novelty_does_not_create_authority": True,
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
                "configuration": (
                    result[
                        "configuration"
                    ]
                ),
                "generations": (
                    generations
                ),
                "recursion_segues": (
                    recursion_segues
                ),
            }
        )

        return result


def self_check() -> dict[str, Any]:
    recursive = (
        RecursiveUnderscore(
            realizer=(
                pipeline_module
                .realization
                .FixtureRealizer()
            ),
            max_generations=2,
            recurse_unresolved=False,
            candidate_count=8,
        )
    )

    payload = {
        "subject": (
            "produce an ending that "
            "subverts conventional victory"
        ),
        "context": (
            "Use already-visible facts."
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
            "chosen one",
            "last-second rescue",
            "secret identity reveal",
        ],
        "constraints": {
            "required": [],
            "forbidden": [],
        },
    }

    result = (
        recursive.execute(
            payload
        )
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

    if (
        result[
            "generation_count"
        ]
        != 1
    ):
        raise RuntimeError(
            "fixture generation "
            "count failed"
        )

    if (
        result[
            "branch_count"
        ]
        != 1
    ):
        raise RuntimeError(
            "fixture branch "
            "count failed"
        )

    if any(
        item.get(
            "authority_effect"
        )
        != "none"
        for item in result[
            "recursion_segues"
        ]
    ):
        raise RuntimeError(
            "recursion segue "
            "authority invariant failed"
        )

    return {
        "schema": (
            schema_version
        ),
        "authority_effect": (
            authority_effect
        ),
        "self_check": (
            "passed"
        ),
        "generation_count": (
            result[
                "generation_count"
            ]
        ),
        "branch_count": (
            result[
                "branch_count"
            ]
        ),
        "recursion_segue_count": len(
            result[
                "recursion_segues"
            ]
        ),
        "final_counts": {
            key: len(
                value
            )
            for key, value
            in result[
                "final_frontier"
            ].items()
        },
        "fingerprint": (
            result[
                "fingerprint"
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-recursive"
        ),
        description=(
            "bounded recursive divergent "
            "generation through vessel "
            "selection pressure"
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

    commands = (
        parser.add_subparsers(
            dest="action",
            required=True,
        )
    )

    execute = (
        commands.add_parser(
            "execute"
        )
    )

    execute.add_argument(
        "--input",
        required=True,
    )

    commands.add_parser(
        "self-check"
    )

    return parser


def main() -> int:
    args = (
        build_parser()
        .parse_args()
    )

    if args.action == (
        "self-check"
    ):
        result = (
            self_check()
        )

    elif args.action == (
        "execute"
    ):
        realizer = (
            pipeline_module
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

        recursive = (
            RecursiveUnderscore(
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
            )
        )

        result = (
            recursive.execute(
                load_json(
                    args.input
                )
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
