#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from primitives import require_object
from primitives import bind_stable_id
from primitives import load_json


schema_version = "savant.underscore.vessel.negative-knowledge.v1"
authority_effect = "none"


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


stable_id = bind_stable_id(digest)

def require_list(
    value: Any,
) -> list[Any]:
    if isinstance(value, list):
        return value

    return []


def normalize_text(value: Any) -> str:
    return " ".join(
        str(value or "").strip().split()
    )


def normalized_key(value: Any) -> str:
    return hashlib.sha256(
        normalize_text(value)
        .casefold()
        .encode("utf-8")
    ).hexdigest()


def candidate_from_record(
    record: Any,
) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None

    candidate = record.get("candidate")

    if isinstance(candidate, dict):
        return candidate

    return None


def flags_from_record(
    record: dict[str, Any],
) -> list[str]:
    values: list[str] = []

    candidate = candidate_from_record(
        record
    )

    if candidate:
        raw = candidate.get(
            "flags",
            [],
        )

        if isinstance(raw, list):
            values.extend(
                str(item).strip()
                for item in raw
                if str(item).strip()
            )

        metadata = candidate.get(
            "metadata",
            {},
        )

        if isinstance(metadata, dict):
            raw = metadata.get(
                "flags",
                [],
            )

            if isinstance(raw, list):
                values.extend(
                    str(item).strip()
                    for item in raw
                    if str(item).strip()
                )

    segue = record.get(
        "segue",
        {},
    )

    if isinstance(segue, dict):
        payload = segue.get(
            "payload",
            {},
        )

        if isinstance(payload, dict):
            raw = payload.get(
                "flags",
                [],
            )

            if isinstance(raw, list):
                values.extend(
                    str(item).strip()
                    for item in raw
                    if str(item).strip()
                )

    return sorted(
        set(values)
    )


def evidence_from_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    candidate = (
        candidate_from_record(record)
        or {}
    )

    return {
        "source_instance_id": (
            str(
                record.get(
                    "source_instance_id",
                    candidate.get(
                        "instance_id",
                        "",
                    ),
                )
            )
        ),
        "text": normalize_text(
            candidate.get(
                "text",
                "",
            )
        ),
        "difference": normalize_text(
            candidate.get(
                "difference",
                "",
            )
        ),
        "lens": candidate.get(
            "lens",
            {},
        ),
        "flags": flags_from_record(
            record
        ),
        "lineage": (
            candidate.get(
                "lineage",
                [],
            )
            if isinstance(
                candidate.get(
                    "lineage",
                    [],
                ),
                list,
            )
            else []
        ),
    }


def packet_for(
    *,
    subject: str,
    classification: str,
    record: dict[str, Any],
    generation: int | None,
) -> dict[str, Any] | None:
    evidence = evidence_from_record(
        record
    )

    text = evidence[
        "text"
    ]

    if not text:
        return None

    flags = evidence[
        "flags"
    ]

    if classification == "rejected":
        lesson_type = (
            "avoid_rejected_pattern"
        )
        disposition = "avoid"

    elif classification == (
        "mutation_terminal"
    ):
        lesson_type = (
            "insufficiently_resolved_pattern"
        )
        disposition = "transform"

    elif classification == (
        "unresolved_terminal"
    ):
        lesson_type = (
            "unresolved_pattern"
        )
        disposition = "investigate"

    elif classification == "unknown":
        lesson_type = (
            "classification_gap"
        )
        disposition = "inspect"

    else:
        return None

    mechanism = (
        flags[0]
        if flags
        else classification
    )

    identity_basis = {
        "subject": subject,
        "classification": classification,
        "lesson_type": lesson_type,
        "mechanism": mechanism,
        "text_key": normalized_key(
            text
        ),
        "generation": generation,
    }

    return {
        "packet_id": stable_id(
            "negative_knowledge",
            identity_basis,
        ),
        "schema": schema_version,
        "owner": "underscore",
        "source": "vessel",
        "authority_effect": (
            authority_effect
        ),
        "knowledge_status": (
            "derived_non_authoritative"
        ),
        "lesson_type": lesson_type,
        "disposition": disposition,
        "subject": subject,
        "mechanism": mechanism,
        "generation": generation,
        "evidence": evidence,
        "reuse_contract": {
            "may_influence_future_divergence": True,
            "may_reduce_repeated_failure": True,
            "may_rank_lenses": True,
            "may_become_canon_automatically": False,
            "may_become_authority_automatically": False,
            "requires_memory_owner_for_durable_recall": True,
            "requires_coda_for_durable_mutation": True,
        },
    }


class NegativeKnowledgeCompiler:
    frontier_keys = (
        "rejected",
        "mutation_terminal",
        "unresolved_terminal",
        "unknown",
    )

    def compile(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        subject = normalize_text(
            payload.get(
                "subject",
                "",
            )
        )

        if not subject:
            raise ValueError(
                "subject is required"
            )

        frontier = require_object(
            payload.get(
                "final_frontier",
                {},
            ),
            "final_frontier",
        )

        generation_by_branch: dict[
            str,
            int,
        ] = {}

        for generation in require_list(
            payload.get(
                "generations",
                [],
            )
        ):
            if not isinstance(
                generation,
                dict,
            ):
                continue

            branch_id = str(
                generation.get(
                    "branch_id",
                    "",
                )
            )

            if branch_id:
                generation_by_branch[
                    branch_id
                ] = int(
                    generation.get(
                        "generation",
                        0,
                    )
                )

        packets = []

        for classification in (
            self.frontier_keys
        ):
            records = require_list(
                frontier.get(
                    classification,
                    [],
                )
            )

            for record in records:
                if not isinstance(
                    record,
                    dict,
                ):
                    continue

                segue = record.get(
                    "segue",
                    {},
                )

                branch_id = ""

                if isinstance(
                    segue,
                    dict,
                ):
                    segue_payload = (
                        segue.get(
                            "payload",
                            {},
                        )
                    )

                    if isinstance(
                        segue_payload,
                        dict,
                    ):
                        branch_id = str(
                            segue_payload.get(
                                "branch_id",
                                "",
                            )
                        )

                generation = (
                    generation_by_branch.get(
                        branch_id
                    )
                    if branch_id
                    else None
                )

                packet = packet_for(
                    subject=subject,
                    classification=(
                        classification
                    ),
                    record=record,
                    generation=(
                        generation
                    ),
                )

                if packet is not None:
                    packets.append(
                        packet
                    )

        deduplicated = {}

        for packet in packets:
            evidence = packet[
                "evidence"
            ]

            key = (
                packet[
                    "lesson_type"
                ],
                packet[
                    "mechanism"
                ],
                normalized_key(
                    evidence[
                        "text"
                    ]
                ),
            )

            deduplicated[
                key
            ] = packet

        packets = sorted(
            deduplicated.values(),
            key=lambda item: (
                item["lesson_type"],
                item["mechanism"],
                item["packet_id"],
            ),
        )

        mechanism_counts = {}

        for packet in packets:
            mechanism = packet[
                "mechanism"
            ]

            mechanism_counts[
                mechanism
            ] = (
                mechanism_counts.get(
                    mechanism,
                    0,
                )
                + 1
            )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "capability": (
                "negative_knowledge_projection"
            ),
            "authority_effect": (
                authority_effect
            ),
            "subject": subject,
            "packet_count": len(
                packets
            ),
            "packets": packets,
            "mechanism_counts": dict(
                sorted(
                    mechanism_counts.items()
                )
            ),
            "memory_contract": {
                "persistent_store_created": False,
                "scrybe_memory_required_for_recall": True,
                "lore_canon_store_duplicated": False,
                "coda_durable_mutation_performed": False,
            },
            "invariants": {
                "projection_only": True,
                "negative_knowledge_is_not_authority": True,
                "failure_is_not_fact": True,
                "candidate_output_is_not_evidence_admission": True,
                "no_independent_memory_store": True,
                "source_lineage_preserved": True,
                "deterministic_packet_identity": True,
            },
        }

        result[
            "fingerprint"
        ] = digest(
            {
                "schema": schema_version,
                "subject": subject,
                "packets": packets,
            }
        )

        return result


def self_check() -> dict[str, Any]:
    payload = {
        "subject": (
            "subvert a conventional "
            "victory ending"
        ),
        "generations": [],
        "final_frontier": {
            "surviving": [],
            "mutation_terminal": [
                {
                    "classification": (
                        "mutation"
                    ),
                    "source_instance_id": (
                        "candidate_1"
                    ),
                    "candidate": {
                        "instance_id": (
                            "candidate_1"
                        ),
                        "text": (
                            "The apparent victory "
                            "simply reveals a secret "
                            "identity."
                        ),
                        "flags": [
                            "baseline_convergence"
                        ],
                        "lineage": [
                            "assignment_1"
                        ],
                    },
                    "segue": {},
                }
            ],
            "unresolved_terminal": [
                {
                    "classification": (
                        "unresolved"
                    ),
                    "source_instance_id": (
                        "candidate_2"
                    ),
                    "candidate": {
                        "instance_id": (
                            "candidate_2"
                        ),
                        "text": (
                            "The winner receives "
                            "exactly what was expected "
                            "but the consequence remains "
                            "structurally unclear."
                        ),
                        "flags": [
                            "novelty_without_survival"
                        ],
                        "lineage": [
                            "assignment_2"
                        ],
                    },
                    "segue": {},
                }
            ],
            "rejected": [
                {
                    "classification": (
                        "rejected"
                    ),
                    "source_instance_id": (
                        "candidate_3"
                    ),
                    "candidate": {
                        "instance_id": (
                            "candidate_3"
                        ),
                        "text": (
                            "It was all a dream."
                        ),
                        "flags": [
                            "cliche_pressure"
                        ],
                        "lineage": [
                            "assignment_3"
                        ],
                    },
                    "segue": {},
                }
            ],
            "unknown": [],
        },
    }

    compiler = (
        NegativeKnowledgeCompiler()
    )

    first = compiler.compile(
        payload
    )

    second = compiler.compile(
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
            "determinism failed"
        )

    if (
        first[
            "packet_count"
        ]
        != 3
    ):
        raise RuntimeError(
            "packet count failed"
        )

    if any(
        packet[
            "authority_effect"
        ]
        != "none"
        for packet in first[
            "packets"
        ]
    ):
        raise RuntimeError(
            "authority invariant failed"
        )

    if first[
        "memory_contract"
    ][
        "persistent_store_created"
    ]:
        raise RuntimeError(
            "memory ownership violated"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "packet_count": (
            first[
                "packet_count"
            ]
        ),
        "mechanism_counts": (
            first[
                "mechanism_counts"
            ]
        ),
        "fingerprint": (
            first[
                "fingerprint"
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-negative-knowledge"
        ),
        description=(
            "derive non-authoritative "
            "negative-knowledge packets "
            "from vessel frontier results"
        ),
    )

    commands = (
        parser.add_subparsers(
            dest="action",
            required=True,
        )
    )

    compile_command = (
        commands.add_parser(
            "compile"
        )
    )

    compile_command.add_argument(
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

    if args.action == "self-check":
        result = self_check()

    elif args.action == "compile":
        result = (
            NegativeKnowledgeCompiler()
            .compile(
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
