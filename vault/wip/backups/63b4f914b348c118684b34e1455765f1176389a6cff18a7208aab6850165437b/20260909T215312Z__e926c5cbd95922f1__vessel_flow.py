#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


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

vessel_runtime_path = (
    underscore_root
    / "runtime"
    / "vessel"
    / "vessel.py"
)

schema_version = "savant.underscore.vessel.flow.v1"
authority_effect = "none"

segue_candidate_ingress = (
    "underscore.divergence.candidate_to_vessel"
)

segue_survival_egress = (
    "underscore.vessel.candidate_to_surviving_frontier"
)

segue_rejection_egress = (
    "underscore.vessel.candidate_to_rejected_frontier"
)

segue_mutation_egress = (
    "underscore.vessel.candidate_to_mutation"
)

segue_unresolved_egress = (
    "underscore.vessel.candidate_to_unresolved"
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
    width: int = 24,
) -> str:
    return f"{prefix}_{digest(value)[:width]}"


def load_vessel_module() -> Any:
    if not vessel_runtime_path.is_file():
        raise RuntimeError(
            "verified vessel runtime is unavailable: "
            f"{vessel_runtime_path}"
        )

    spec = importlib.util.spec_from_file_location(
        "savant_underscore_vessel_runtime",
        vessel_runtime_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "unable to load vessel runtime specification"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


@dataclass(frozen=True)
class SegueEnvelope:
    segue_id: str
    segue_type: str
    owner: str
    source_instance_id: str | None
    target: str
    authority_effect: str
    payload: dict[str, Any]
    provenance: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "segue_id": self.segue_id,
            "segue_type": self.segue_type,
            "owner": self.owner,
            "source_instance_id": (
                self.source_instance_id
            ),
            "target": self.target,
            "authority_effect": (
                self.authority_effect
            ),
            "payload": self.payload,
            "provenance": self.provenance,
        }


def make_segue(
    *,
    segue_type: str,
    source_instance_id: str | None,
    target: str,
    payload: dict[str, Any],
    provenance: dict[str, Any],
) -> SegueEnvelope:
    identity = {
        "schema": schema_version,
        "segue_type": segue_type,
        "source_instance_id": (
            source_instance_id
        ),
        "target": target,
        "payload": payload,
        "provenance": provenance,
    }

    return SegueEnvelope(
        segue_id=stable_id(
            "segue",
            identity,
        ),
        segue_type=segue_type,
        owner="underscore",
        source_instance_id=(
            source_instance_id
        ),
        target=target,
        authority_effect=authority_effect,
        payload=payload,
        provenance=provenance,
    )


def normalize_candidate(
    candidate: Any,
    index: int,
) -> dict[str, Any]:
    if isinstance(candidate, str):
        text = candidate.strip()

        if not text:
            raise ValueError(
                f"candidate {index} is empty"
            )

        candidate_id = stable_id(
            "instance",
            {
                "owner": "underscore",
                "index": index,
                "text": text,
            },
        )

        return {
            "instance_id": candidate_id,
            "text": text,
            "source": "underscore",
            "lineage": [],
            "metadata": {},
        }

    if not isinstance(candidate, dict):
        raise TypeError(
            f"candidate {index} must be string or object"
        )

    text = str(
        candidate.get("text", "")
    ).strip()

    if not text:
        raise ValueError(
            f"candidate {index} has no text"
        )

    instance_id = str(
        candidate.get(
            "instance_id",
            candidate.get(
                "candidate_id",
                "",
            ),
        )
    ).strip()

    if not instance_id:
        instance_id = stable_id(
            "instance",
            {
                "owner": "underscore",
                "index": index,
                "text": text,
            },
        )

    lineage_raw = candidate.get(
        "lineage",
        [],
    )

    if not isinstance(
        lineage_raw,
        list,
    ):
        lineage_raw = []

    lineage = [
        str(item).strip()
        for item in lineage_raw
        if str(item).strip()
    ]

    metadata = candidate.get(
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    return {
        "instance_id": instance_id,
        "text": text,
        "source": str(
            candidate.get(
                "source",
                "underscore",
            )
        ).strip()
        or "underscore",
        "lineage": lineage,
        "metadata": metadata,
    }


def normalize_candidates(
    values: Iterable[Any],
) -> list[dict[str, Any]]:
    return [
        normalize_candidate(
            value,
            index,
        )
        for index, value
        in enumerate(values)
    ]


def vessel_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    lineage = list(
        candidate["lineage"]
    )

    lineage.append(
        candidate["instance_id"]
    )

    return {
        "text": candidate["text"],
        "source": candidate["source"],
        "lineage": lineage,
    }


def candidate_map(
    candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        candidate["text"]: candidate
        for candidate in candidates
    }


def classify_candidate(
    score: dict[str, Any],
    *,
    survival_ids: set[str],
    pareto_ids: set[str],
) -> str:
    candidate_id = str(
        score.get(
            "candidate_id",
            "",
        )
    )

    survivability = float(
        score.get(
            "survivability_score",
            0.0,
        )
    )

    constraint_score = float(
        score.get(
            "constraint_score",
            0.0,
        )
    )

    cliche_risk = float(
        score.get(
            "cliche_risk",
            1.0,
        )
    )

    flags = set(
        str(value)
        for value
        in score.get(
            "flags",
            [],
        )
    )

    if candidate_id in survival_ids:
        return "surviving"

    if (
        candidate_id in pareto_ids
        and constraint_score >= 0.70
    ):
        return "surviving"

    if (
        "constraint_escape" in flags
        or constraint_score < 0.50
    ):
        return "rejected"

    if (
        "cliche_pressure" in flags
        and cliche_risk >= 0.78
    ):
        return "mutation"

    if survivability < 0.45:
        return "mutation"

    return "unresolved"


class VesselFlow:
    def __init__(
        self,
        *,
        cliche_threshold: float,
        similarity_threshold: float,
        frontier_size: int,
        mmr_lambda: float,
    ) -> None:
        vessel_module = (
            load_vessel_module()
        )

        self.engine = (
            vessel_module.Vessel(
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
        raw_candidates = payload.get(
            "candidates",
            [],
        )

        if not isinstance(
            raw_candidates,
            list,
        ):
            raise TypeError(
                "candidates must be a list"
            )

        if len(raw_candidates) < 2:
            raise ValueError(
                "underscore vessel flow requires "
                "at least two divergent candidates"
            )

        candidates = (
            normalize_candidates(
                raw_candidates
            )
        )

        ingress_segues = []

        for candidate in candidates:
            ingress_segues.append(
                make_segue(
                    segue_type=(
                        segue_candidate_ingress
                    ),
                    source_instance_id=(
                        candidate[
                            "instance_id"
                        ]
                    ),
                    target=(
                        "underscore.vessel"
                    ),
                    payload={
                        "text": (
                            candidate["text"]
                        ),
                        "source": (
                            candidate[
                                "source"
                            ]
                        ),
                        "lineage": (
                            candidate[
                                "lineage"
                            ]
                        ),
                    },
                    provenance={
                        "source": (
                            candidate[
                                "source"
                            ]
                        ),
                        "metadata": (
                            candidate[
                                "metadata"
                            ]
                        ),
                    },
                )
            )

        vessel_payload = {
            "subject": str(
                payload.get(
                    "subject",
                    "",
                )
            ).strip(),
            "candidates": [
                vessel_candidate(
                    candidate
                )
                for candidate
                in candidates
            ],
            "baselines": payload.get(
                "baselines",
                [],
            ),
            "cliches": payload.get(
                "cliches",
                [],
            ),
            "constraints": payload.get(
                "constraints",
                {},
            ),
        }

        vessel_result = (
            self.engine.analyze(
                vessel_payload
            )
        )

        survival_ids = {
            str(item["candidate_id"])
            for item
            in vessel_result.get(
                "divergent_frontier",
                [],
            )
            if isinstance(
                item,
                dict,
            )
            and item.get(
                "candidate_id"
            )
        }

        pareto_ids = set(
            str(value)
            for value
            in vessel_result.get(
                "pareto_frontier",
                [],
            )
        )

        by_text = candidate_map(
            candidates
        )

        egress_segues = []
        surviving = []
        rejected = []
        mutation = []
        unresolved = []

        for score in vessel_result.get(
            "ranked_candidates",
            [],
        ):
            if not isinstance(
                score,
                dict,
            ):
                continue

            text = str(
                score.get(
                    "text",
                    "",
                )
            )

            source_candidate = (
                by_text.get(text)
            )

            source_instance_id = None

            if source_candidate:
                source_instance_id = (
                    source_candidate[
                        "instance_id"
                    ]
                )

            classification = (
                classify_candidate(
                    score,
                    survival_ids=(
                        survival_ids
                    ),
                    pareto_ids=(
                        pareto_ids
                    ),
                )
            )

            projection = {
                "instance_id": (
                    source_instance_id
                ),
                "vessel_candidate_id": (
                    score.get(
                        "candidate_id"
                    )
                ),
                "classification": (
                    classification
                ),
                "text": text,
                "survivability_score": (
                    score.get(
                        "survivability_score"
                    )
                ),
                "subversion_score": (
                    score.get(
                        "subversion_score"
                    )
                ),
                "divergence_score": (
                    score.get(
                        "divergence_score"
                    )
                ),
                "cliche_risk": (
                    score.get(
                        "cliche_risk"
                    )
                ),
                "constraint_score": (
                    score.get(
                        "constraint_score"
                    )
                ),
                "flags": score.get(
                    "flags",
                    [],
                ),
                "discriminants": (
                    score.get(
                        "discriminants",
                        [],
                    )
                ),
            }

            provenance = {
                "vessel_run_id": (
                    vessel_result[
                        "run_id"
                    ]
                ),
                "vessel_fingerprint": (
                    vessel_result[
                        "fingerprint"
                    ]
                ),
                "source_instance_id": (
                    source_instance_id
                ),
                "authority_effect": (
                    authority_effect
                ),
            }

            if classification == (
                "surviving"
            ):
                segue_type = (
                    segue_survival_egress
                )

                target = (
                    "underscore.divergence."
                    "surviving_frontier"
                )

                surviving.append(
                    projection
                )

            elif classification == (
                "rejected"
            ):
                segue_type = (
                    segue_rejection_egress
                )

                target = (
                    "underscore.divergence."
                    "rejected_frontier"
                )

                rejected.append(
                    projection
                )

            elif classification == (
                "mutation"
            ):
                segue_type = (
                    segue_mutation_egress
                )

                target = (
                    "underscore.divergence."
                    "mutation_frontier"
                )

                mutation.append(
                    projection
                )

            else:
                segue_type = (
                    segue_unresolved_egress
                )

                target = (
                    "underscore.divergence."
                    "unresolved_frontier"
                )

                unresolved.append(
                    projection
                )

            egress_segues.append(
                make_segue(
                    segue_type=(
                        segue_type
                    ),
                    source_instance_id=(
                        source_instance_id
                    ),
                    target=target,
                    payload=projection,
                    provenance=(
                        provenance
                    ),
                )
            )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "authority_effect": (
                authority_effect
            ),
            "subject": vessel_payload[
                "subject"
            ],
            "vessel_run_id": (
                vessel_result["run_id"]
            ),
            "vessel_fingerprint": (
                vessel_result[
                    "fingerprint"
                ]
            ),
            "input_instances": (
                candidates
            ),
            "segues": {
                "ingress": [
                    item.as_dict()
                    for item
                    in ingress_segues
                ],
                "egress": [
                    item.as_dict()
                    for item
                    in egress_segues
                ],
            },
            "frontiers": {
                "surviving": surviving,
                "mutation": mutation,
                "unresolved": unresolved,
                "rejected": rejected,
            },
            "counts": {
                "input": len(
                    candidates
                ),
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
            },
            "invariants": {
                "projection_only": True,
                "novelty_is_not_authority": True,
                "vessel_may_not_promote_canon": True,
                "rejected_candidate_is_not_false": True,
                "unresolved_remains_unresolved": True,
                "source_instances_preserved": True,
                "lineage_preserved": True,
                "typed_segue_identity_deterministic": True,
            },
        }

        result["fingerprint"] = (
            digest(
                {
                    "schema": (
                        schema_version
                    ),
                    "subject": result[
                        "subject"
                    ],
                    "vessel_fingerprint": (
                        result[
                            "vessel_fingerprint"
                        ]
                    ),
                    "segues": result[
                        "segues"
                    ],
                    "frontiers": (
                        result[
                            "frontiers"
                        ]
                    ),
                }
            )
        )

        return result


def load_payload(
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

    payload = json.loads(raw)

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "input must be a JSON object"
        )

    return payload


def self_check() -> dict[str, Any]:
    flow = VesselFlow(
        cliche_threshold=0.68,
        similarity_threshold=0.74,
        frontier_size=3,
        mmr_lambda=0.68,
    )

    payload = {
        "subject": (
            "subvert a conventional victory"
        ),
        "baselines": [
            (
                "the hero defeats the villain "
                "and everyone celebrates"
            )
        ],
        "cliches": [
            "the chosen one",
            "saved at the last second",
            "everyone celebrates",
        ],
        "constraints": {
            "required": [],
            "forbidden": [],
        },
        "candidates": [
            {
                "instance_id": (
                    "underscore_test_1"
                ),
                "source": (
                    "underscore.self_check"
                ),
                "text": (
                    "the hero defeats the villain "
                    "and everyone celebrates"
                ),
            },
            {
                "instance_id": (
                    "underscore_test_2"
                ),
                "source": (
                    "underscore.self_check"
                ),
                "text": (
                    "the victory succeeds but "
                    "proves the defeated enemy's "
                    "central accusation was correct"
                ),
            },
            {
                "instance_id": (
                    "underscore_test_3"
                ),
                "source": (
                    "underscore.self_check"
                ),
                "text": (
                    "the apparent contest ends "
                    "because the protagonist changes "
                    "what winning means before either "
                    "side can complete it"
                ),
            },
        ],
    }

    result = flow.execute(
        payload
    )

    if result[
        "authority_effect"
    ] != "none":
        raise RuntimeError(
            "authority invariant failed"
        )

    if len(
        result["segues"]["ingress"]
    ) != 3:
        raise RuntimeError(
            "candidate ingress projection failed"
        )

    if len(
        result["segues"]["egress"]
    ) != 3:
        raise RuntimeError(
            "candidate egress projection failed"
        )

    if (
        sum(
            result["counts"][key]
            for key in (
                "surviving",
                "mutation",
                "unresolved",
                "rejected",
            )
        )
        != 3
    ):
        raise RuntimeError(
            "frontier accounting failed"
        )

    for envelope in (
        result["segues"]["ingress"]
        + result["segues"]["egress"]
    ):
        if (
            envelope[
                "authority_effect"
            ]
            != "none"
        ):
            raise RuntimeError(
                "segue authority invariant failed"
            )

        if not str(
            envelope["segue_type"]
        ).startswith(
            "underscore."
        ):
            raise RuntimeError(
                "segue ownership invariant failed"
            )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "input_instances": (
            result["counts"]["input"]
        ),
        "ingress_segues": len(
            result["segues"]["ingress"]
        ),
        "egress_segues": len(
            result["segues"]["egress"]
        ),
        "frontiers": (
            result["counts"]
        ),
        "vessel_run_id": (
            result["vessel_run_id"]
        ),
        "fingerprint": (
            result["fingerprint"]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="underscore-vessel-flow",
        description=(
            "rubric-owned underscore vessel "
            "candidate discrimination flow"
        ),
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

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    execute = commands.add_parser(
        "execute"
    )

    execute.add_argument(
        "--input",
        required=True,
        help=(
            "JSON input path or - for stdin"
        ),
    )

    commands.add_parser(
        "self-check"
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "self-check":
        result = self_check()

    elif args.command == "execute":
        flow = VesselFlow(
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

        result = flow.execute(
            load_payload(
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
    raise SystemExit(main())
