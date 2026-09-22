#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


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


def stable_id(
    prefix: str,
    value: Any,
    width: int = 24,
) -> str:
    return (
        f"{prefix}_"
        f"{digest(value)[:width]}"
    )


def normalize_text(
    value: Any,
) -> str:
    return " ".join(
        str(
            value
            or ""
        )
        .casefold()
        .split()
    )


def semantic_key(
    text: Any,
) -> str:
    return hashlib.sha256(
        normalize_text(
            text
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def require_object(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            f"{name} must be an object"
        )

    return value


def require_list(
    value: Any,
    name: str,
) -> list[Any]:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError(
            f"{name} must be a list"
        )

    return value


def load_module(
    name: str,
    path: Path,
) -> Any:
    if not path.is_file():
        raise RuntimeError(
            f"required module unavailable: "
            f"{path}"
        )

    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"unable to load module: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


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
    def realized_index(
        generation_result: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        output: dict[
            str,
            dict[str, Any],
        ] = {}

        realization_stage = (
            generation_result.get(
                "_realized_instances",
                [],
            )
        )

        if isinstance(
            realization_stage,
            list,
        ):
            for candidate in (
                realization_stage
            ):
                if not isinstance(
                    candidate,
                    dict,
                ):
                    continue

                instance_id = str(
                    candidate.get(
                        "instance_id",
                        "",
                    )
                ).strip()

                if instance_id:
                    output[
                        instance_id
                    ] = candidate

        return output

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
    def extract_text(
        candidate: dict[str, Any],
    ) -> str:
        return str(
            candidate.get(
                "text",
                "",
            )
        ).strip()

    def seeds_from_result(
        self,
        result: dict[str, Any],
        candidate_index: dict[
            str,
            dict[str, Any],
        ],
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        surviving = []
        mutation = []
        unresolved = []
        rejected = []
        unknown = []

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

            candidate = (
                candidate_index.get(
                    source_id
                )
            )

            record = {
                "classification": (
                    classification
                ),
                "source_instance_id": (
                    source_id
                ),
                "candidate": candidate,
                "segue": segue,
            }

            if classification == (
                "surviving"
            ):
                surviving.append(
                    record
                )

            elif classification == (
                "mutation"
            ):
                mutation.append(
                    record
                )

            elif classification == (
                "unresolved"
            ):
                unresolved.append(
                    record
                )

            elif classification == (
                "rejected"
            ):
                rejected.append(
                    record
                )

            else:
                unknown.append(
                    record
                )

        return (
            surviving,
            mutation,
            unresolved,
            rejected,
            unknown,
        )

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
                "recursive seed does not "
                "resolve to a realized candidate"
            )

        text = self.extract_text(
            candidate
        )

        if not text:
            raise ValueError(
                "recursive seed contains "
                "no candidate text"
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
            "This is a recursive underscore "
            f"generation {generation}. "
            "The previous candidate survived "
            "initial realization but Vessel "
            f"classified it as {classification}. "
            "Do not merely paraphrase it. "
            "Alter its governing assumption, "
            "mechanism, causal structure, "
            "information structure, constraint "
            "interaction, or expected payoff "
            "while preserving hard constraints."
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
                []
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
        )

        if source_instance_id:
            lineage.append(
                source_instance_id
            )

        return {
            "subject": (
                root_payload.get(
                    "subject",
                    ""
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
                "generation": (
                    generation
                ),
                "source_instance_id": (
                    source_instance_id
                ),
                "source_classification": (
                    classification
                ),
                "lineage": (
                    lineage
                ),
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

        generation_queue = [
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
        rejected_records = []
        unresolved_terminal = []
        mutation_terminal = []
        unknown_terminal = []

        seen_texts: set[str] = set()
        seen_branches: set[str] = set()

        recursion_segues = []

        while generation_queue:
            branch = (
                generation_queue.pop(0)
            )

            generation = int(
                branch[
                    "generation"
                ]
            )

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

            candidate_index: dict[
                str,
                dict[str, Any],
            ] = {}

            realization_meta = (
                result.get(
                    "_realized_instances",
                    []
                )
            )

            if isinstance(
                realization_meta,
                list,
            ):
                for item in (
                    realization_meta
                ):
                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    instance_id = str(
                        item.get(
                            "instance_id",
                            "",
                        )
                    ).strip()

                    if instance_id:
                        candidate_index[
                            instance_id
                        ] = item

            if not candidate_index:
                for segue in (
                    self.egress(
                        result
                    )
                ):
                    payload_data = (
                        segue.get(
                            "payload",
                            {},
                        )
                    )

                    if not isinstance(
                        payload_data,
                        dict,
                    ):
                        continue

                    embedded = (
                        payload_data.get(
                            "candidate"
                        )
                    )

                    if not isinstance(
                        embedded,
                        dict,
                    ):
                        continue

                    instance_id = str(
                        embedded.get(
                            "instance_id",
                            source_id_from_segue(
                                segue
                            ),
                        )
                    ).strip()

                    if instance_id:
                        candidate_index[
                            instance_id
                        ] = embedded

            (
                surviving,
                mutation,
                unresolved,
                rejected,
                unknown,
            ) = self.seeds_from_result(
                result,
                candidate_index,
            )

            generation_record = {
                "generation": (
                    generation
                ),
                "branch_id": (
                    branch_id
                ),
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
                "stage_summary": (
                    result.get(
                        "stages",
                        {},
                    )
                ),
                "counts": {
                    "surviving": len(
                        surviving
                    ),
                    "mutation": len(
                        mutation
                    ),
                    "unresolved": len(
                        unresolved
                    ),
                    "rejected": len(
                        rejected
                    ),
                    "unknown": len(
                        unknown
                    ),
                },
            }

            generations.append(
                generation_record
            )

            survivors.extend(
                surviving
            )

            rejected_records.extend(
                rejected
            )

            unknown_terminal.extend(
                unknown
            )

            recursive_seeds = list(
                mutation
            )

            if self.recurse_unresolved:
                recursive_seeds.extend(
                    unresolved
                )

            else:
                unresolved_terminal.extend(
                    unresolved
                )

            if (
                generation + 1
                >= self.max_generations
            ):
                mutation_terminal.extend(
                    mutation
                )

                if self.recurse_unresolved:
                    unresolved_terminal.extend(
                        unresolved
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
                        mutation_terminal.append(
                            seed
                        )

                    elif (
                        seed.get(
                            "classification"
                        )
                        == "unresolved"
                    ):
                        unresolved_terminal.append(
                            seed
                        )

                    continue

                text = self.extract_text(
                    candidate
                )

                if not text:
                    continue

                text_key = semantic_key(
                    text
                )

                if text_key in (
                    seen_texts
                ):
                    continue

                seen_texts.add(
                    text_key
                )

                next_generation = (
                    generation + 1
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
                )

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
                    "segue_id": (
                        stable_id(
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
                        )
                    ),
                    "segue_type": (
                        "underscore.vessel."
                        "frontier_to_divergence"
                    ),
                    "owner": (
                        "underscore"
                    ),
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

                generation_queue.append(
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
            "schema": (
                schema_version
            ),
            "owner": (
                "underscore"
            ),
            "rubric": (
                "vessel"
            ),
            "authority_effect": (
                authority_effect
            ),
            "subject": (
                subject
            ),
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
            "generation_count": (
                len(
                    {
                        item[
                            "generation"
                        ]
                        for item
                        in generations
                    }
                )
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
                    mutation_terminal
                ),
                "unresolved_terminal": (
                    unresolved_terminal
                ),
                "rejected": (
                    rejected_records
                ),
                "unknown": (
                    unknown_terminal
                ),
            },
            "recursion_segues": (
                recursion_segues
            ),
            "invariants": {
                "authority_effect_none": (
                    True
                ),
                "bounded_recursion": (
                    True
                ),
                "rejected_candidates_do_not_recurse": (
                    True
                ),
                "surviving_candidates_do_not_recurse": (
                    True
                ),
                "mutation_candidates_may_recurse": (
                    True
                ),
                "unresolved_recursion_is_configurable": (
                    True
                ),
                "duplicate_text_branches_suppressed": (
                    True
                ),
                "generation_lineage_preserved": (
                    True
                ),
                "novelty_does_not_create_authority": (
                    True
                ),
            },
        }

        result[
            "fingerprint"
        ] = digest(
            {
                "schema": (
                    schema_version
                ),
                "subject": (
                    subject
                ),
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
    realizer = (
        pipeline_module.realization
        .FixtureRealizer()
    )

    recursive = (
        RecursiveUnderscore(
            realizer=realizer,
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

    result = recursive.execute(
        payload
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
            "bounded fixture generation "
            "check failed"
        )

    if (
        result[
            "branch_count"
        ]
        != 1
    ):
        raise RuntimeError(
            "fixture branch count failed"
        )

    if any(
        item.get(
            "authority_effect"
        )
        != "none"
        for item
        in result[
            "recursion_segues"
        ]
    ):
        raise RuntimeError(
            "recursion segue authority "
            "invariant failed"
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
        "recursion_segue_count": (
            len(
                result[
                    "recursion_segues"
                ]
            )
        ),
        "fingerprint": (
            result[
                "fingerprint"
            ]
        ),
    }


def load_json(
    path: str,
) -> dict[str, Any]:
    if path == "-":
        raw = (
            sys.stdin.read()
        )

    else:
        raw = (
            Path(
                path
            ).read_text(
                encoding="utf-8"
            )
        )

    return require_object(
        json.loads(
            raw
        ),
        "input",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-recursive"
        ),
        description=(
            "bounded recursive divergent "
            "generation through Vessel "
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
        default=(
            "fixture"
        ),
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
        action=argparse.BooleanOptionalAction,
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
