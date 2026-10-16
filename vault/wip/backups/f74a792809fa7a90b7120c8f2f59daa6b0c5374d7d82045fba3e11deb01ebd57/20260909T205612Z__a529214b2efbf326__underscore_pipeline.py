#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import os
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

vessel_rubric_root = (
    underscore_root
    / "rubric"
    / "vessel"
)

source_root = (
    vessel_rubric_root
    / "source"
)

divergence_path = (
    source_root
    / "divergence_compiler.py"
)

realization_path = (
    source_root
    / "realization_adapter.py"
)

vessel_flow_path = (
    source_root
    / "vessel_flow.py"
)

schema_version = (
    "savant.underscore.pipeline.v1"
)

authority_effect = "none"


def load_module(
    name: str,
    path: Path,
) -> Any:
    if not path.is_file():
        raise RuntimeError(
            f"required module unavailable: {path}"
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


divergence = load_module(
    "savant_underscore_divergence",
    divergence_path,
)

realization = load_module(
    "savant_underscore_realization",
    realization_path,
)

vessel_flow = load_module(
    "savant_underscore_vessel_flow",
    vessel_flow_path,
)


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


def load_json(
    path: str,
) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()

    else:
        raw = Path(
            path
        ).read_text(
            encoding="utf-8"
        )

    return require_object(
        json.loads(raw),
        "input",
    )


def build_realizer(
    adapter: str,
    *,
    records: str | None,
    command: str | None,
    timeout: int,
    max_output_bytes: int,
) -> Any:
    if adapter == "fixture":
        return (
            realization.FixtureRealizer()
        )

    if adapter == "recorded":
        if not records:
            raise ValueError(
                "--records is required "
                "for recorded realization"
            )

        return (
            realization.recorded_realizer(
                records
            )
        )

    if adapter == (
        "external-command"
    ):
        command_text = (
            command
            or os.environ.get(
                "SAVANT_UNDERSCORE_REALIZER_COMMAND",
                "",
            )
        ).strip()

        if not command_text:
            raise ValueError(
                "external-command realization "
                "requires --command or "
                "SAVANT_UNDERSCORE_REALIZER_COMMAND"
            )

        import shlex

        return (
            realization.ExternalCommandRealizer(
                shlex.split(
                    command_text
                ),
                timeout_seconds=timeout,
                max_output_bytes=(
                    max_output_bytes
                ),
            )
        )

    raise ValueError(
        f"unsupported adapter: {adapter}"
    )


class UnderscorePipeline:
    def __init__(
        self,
        *,
        realizer: Any,
        cliche_threshold: float,
        similarity_threshold: float,
        frontier_size: int,
        mmr_lambda: float,
    ) -> None:
        self.compiler = (
            divergence.DivergenceCompiler()
        )

        self.realization = (
            realization.RealizationAdapter(
                realizer
            )
        )

        self.vessel = (
            vessel_flow.VesselFlow(
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

    def execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        compiled = (
            self.compiler.compile(
                payload
            )
        )

        if (
            compiled.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "divergence authority "
                "invariant failed"
            )

        realized = (
            self.realization.execute(
                compiled
            )
        )

        if (
            realized.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "realization authority "
                "invariant failed"
            )

        realized_instances = (
            realized.get(
                "realized_instances",
                [],
            )
        )

        if not realized_instances:
            raise RuntimeError(
                "no candidates were realized"
            )

        candidates = []

        for instance in (
            realized_instances
        ):
            candidates.append(
                {
                    "instance_id": (
                        instance[
                            "instance_id"
                        ]
                    ),
                    "text": (
                        instance[
                            "text"
                        ]
                    ),
                    "source": (
                        instance.get(
                            "source",
                            "underscore.realization",
                        )
                    ),
                    "lineage": (
                        instance.get(
                            "lineage",
                            [],
                        )
                    ),
                    "metadata": {
                        **instance.get(
                            "metadata",
                            {},
                        ),
                        "source_assignment_id": (
                            instance.get(
                                "source_assignment_id"
                            )
                        ),
                        "lens": (
                            instance.get(
                                "lens",
                                {},
                            )
                        ),
                    },
                }
            )

        vessel_payload = {
            "subject": (
                payload.get(
                    "subject",
                    "",
                )
            ),
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
        }

        selected = (
            self.vessel.execute(
                vessel_payload
            )
        )

        if (
            selected.get(
                "authority_effect"
            )
            != "none"
        ):
            raise RuntimeError(
                "vessel authority "
                "invariant failed"
            )

        pipeline_segues = {
            "divergence": (
                compiled.get(
                    "segues",
                    []
                )
            ),
            "realization": (
                realized.get(
                    "segues",
                    []
                )
            ),
            "vessel_ingress": (
                selected.get(
                    "segues",
                    {}
                ).get(
                    "ingress",
                    [],
                )
            ),
            "vessel_egress": (
                selected.get(
                    "segues",
                    {}
                ).get(
                    "egress",
                    [],
                )
            ),
        }

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "authority_effect": (
                authority_effect
            ),
            "subject": (
                payload.get(
                    "subject",
                    "",
                )
            ),
            "stages": {
                "divergence": {
                    "schema": (
                        compiled.get(
                            "schema"
                        )
                    ),
                    "candidate_count": (
                        compiled.get(
                            "candidate_count"
                        )
                    ),
                    "fingerprint": (
                        compiled.get(
                            "fingerprint"
                        )
                    ),
                },
                "realization": {
                    "schema": (
                        realized.get(
                            "schema"
                        )
                    ),
                    "adapter": (
                        realized.get(
                            "adapter"
                        )
                    ),
                    "input_count": (
                        realized.get(
                            "input_count"
                        )
                    ),
                    "realized_count": (
                        realized.get(
                            "realized_count"
                        )
                    ),
                    "failure_count": (
                        realized.get(
                            "failure_count"
                        )
                    ),
                    "fingerprint": (
                        realized.get(
                            "fingerprint"
                        )
                    ),
                },
                "vessel": {
                    "schema": (
                        selected.get(
                            "schema"
                        )
                    ),
                    "run_id": (
                        selected.get(
                            "vessel_run_id"
                        )
                    ),
                    "fingerprint": (
                        selected.get(
                            "fingerprint"
                        )
                    ),
                    "counts": (
                        selected.get(
                            "counts",
                            {},
                        )
                    ),
                },
            },
            "frontiers": (
                selected.get(
                    "frontiers",
                    {},
                )
            ),
            "segues": (
                pipeline_segues
            ),
            "realization_failures": (
                realized.get(
                    "failures",
                    [],
                )
            ),
            "invariants": {
                "projection_only": True,
                "authority_effect_none": True,
                "generated_content_is_not_authority": True,
                "novelty_is_not_authority": True,
                "divergence_precedes_realization": True,
                "realization_precedes_selection": True,
                "candidate_lineage_preserved": True,
                "provider_independent": True,
                "provider_failure_localized": True,
                "vessel_may_not_promote_canon": True,
            },
        }

        return result


def self_check() -> dict[str, Any]:
    pipeline = (
        UnderscorePipeline(
            realizer=(
                realization.FixtureRealizer()
            ),
            cliche_threshold=0.68,
            similarity_threshold=0.74,
            frontier_size=5,
            mmr_lambda=0.68,
        )
    )

    payload = {
        "subject": (
            "produce an ending that "
            "subverts a conventional "
            "victory"
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
    }

    result = (
        pipeline.execute(
            payload
        )
    )

    stages = result[
        "stages"
    ]

    if (
        result[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "pipeline authority "
            "invariant failed"
        )

    if (
        stages[
            "divergence"
        ][
            "candidate_count"
        ]
        != 8
    ):
        raise RuntimeError(
            "divergence count failed"
        )

    if (
        stages[
            "realization"
        ][
            "realized_count"
        ]
        != 8
    ):
        raise RuntimeError(
            "realization count failed"
        )

    if (
        stages[
            "realization"
        ][
            "failure_count"
        ]
        != 0
    ):
        raise RuntimeError(
            "unexpected realization "
            "failure"
        )

    vessel_counts = (
        stages[
            "vessel"
        ][
            "counts"
        ]
    )

    if (
        vessel_counts.get(
            "input"
        )
        != 8
    ):
        raise RuntimeError(
            "vessel input count failed"
        )

    classified = sum(
        int(
            vessel_counts.get(
                key,
                0,
            )
        )
        for key in (
            "surviving",
            "mutation",
            "unresolved",
            "rejected",
        )
    )

    if classified != 8:
        raise RuntimeError(
            "frontier accounting failed"
        )

    if len(
        result[
            "segues"
        ][
            "divergence"
        ]
    ) != 8:
        raise RuntimeError(
            "divergence segue "
            "count failed"
        )

    if len(
        result[
            "segues"
        ][
            "realization"
        ]
    ) != 8:
        raise RuntimeError(
            "realization segue "
            "count failed"
        )

    if len(
        result[
            "segues"
        ][
            "vessel_ingress"
        ]
    ) != 8:
        raise RuntimeError(
            "vessel ingress "
            "count failed"
        )

    if len(
        result[
            "segues"
        ][
            "vessel_egress"
        ]
    ) != 8:
        raise RuntimeError(
            "vessel egress "
            "count failed"
        )

    return {
        "schema": (
            schema_version
        ),
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "candidate_count": (
            stages[
                "divergence"
            ][
                "candidate_count"
            ]
        ),
        "realized_count": (
            stages[
                "realization"
            ][
                "realized_count"
            ]
        ),
        "realization_failures": (
            stages[
                "realization"
            ][
                "failure_count"
            ]
        ),
        "vessel_counts": (
            vessel_counts
        ),
        "segue_counts": {
            key: len(
                value
            )
            for key, value
            in result[
                "segues"
            ].items()
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-pipeline"
        ),
        description=(
            "compose underscore divergence, "
            "realization, and vessel "
            "selection"
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
        help=(
            "underscore request JSON "
            "path or - for stdin"
        ),
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
            build_realizer(
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
            UnderscorePipeline(
                realizer=realizer,
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
            pipeline.execute(
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
