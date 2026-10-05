#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from primitives import bind_stable_id
from primitives import normalize_strings
from primitives import load_payload


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

schema_version = "savant.underscore.divergence.compiler.v1"
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

@dataclass(frozen=True)
class Lens:
    id: str
    family: str
    objective: str
    prohibition: str
    representation: str


lenses: tuple[Lens, ...] = (
    Lens(
        "assumption_inversion",
        "inversion",
        "Identify the strongest hidden assumption and construct a solution that requires its opposite.",
        "Do not merely negate the conclusion.",
        "assumption_graph",
    ),
    Lens(
        "agency_inversion",
        "inversion",
        "Move decisive agency to the participant, subsystem, or force least expected to possess it.",
        "Do not change established capabilities without support.",
        "agency_graph",
    ),
    Lens(
        "goal_inversion",
        "inversion",
        "Treat attaining the apparent goal as the source of the deeper problem.",
        "Do not manufacture arbitrary punishment.",
        "goal_consequence_graph",
    ),
    Lens(
        "cause_effect_reversal",
        "causal",
        "Test whether the apparent effect can coherently become the cause.",
        "Preserve causal legibility.",
        "causal_graph",
    ),
    Lens(
        "constraint_engine",
        "constraint",
        "Use the hardest constraint as the mechanism that generates the solution.",
        "Do not relax the constraint.",
        "constraint_system",
    ),
    Lens(
        "false_binary",
        "categorical",
        "Demonstrate that the apparent either-or framing omits a structurally different option.",
        "The third option must not be a compromise between the first two.",
        "choice_topology",
    ),
    Lens(
        "category_escape",
        "categorical",
        "Test whether the problem has been assigned to the wrong conceptual category.",
        "Do not relabel without changing the operative mechanism.",
        "category_graph",
    ),
    Lens(
        "orthogonal_resolution",
        "lateral",
        "Resolve the underlying pressure without directly solving the stated surface problem.",
        "Do not evade required constraints.",
        "orthogonal_problem_map",
    ),
    Lens(
        "mechanism_substitution",
        "mechanism",
        "Preserve the pressure and outcome while replacing the conventional mechanism producing them.",
        "Surface novelty alone is insufficient.",
        "mechanism_graph",
    ),
    Lens(
        "surface_substitution",
        "mechanism",
        "Preserve the causal engine while expressing it through a radically different surface form.",
        "Do not change the underlying causal logic.",
        "surface_mechanism_split",
    ),
    Lens(
        "negative_space",
        "absence",
        "Build the solution around the important event that never occurs.",
        "The absence must have causal force.",
        "negative_event_graph",
    ),
    Lens(
        "information_asymmetry",
        "information",
        "Change who knows the decisive information and derive consequences from that distribution.",
        "Do not rely on arbitrary concealment.",
        "knowledge_graph",
    ),
    Lens(
        "temporal_dislocation",
        "temporal",
        "Move the decisive cause earlier or later and let its significance emerge through consequences.",
        "Do not use chronology merely to hide information.",
        "timeline",
    ),
    Lens(
        "deferred_meaning",
        "temporal",
        "Make an ordinary earlier element acquire a radically different meaning after later evidence.",
        "The earlier element must remain fair in retrospect.",
        "retrospective_timeline",
    ),
    Lens(
        "scale_translation",
        "scale",
        "Translate the mechanism to a radically different physical, social, organizational, or temporal scale.",
        "Preserve governing relationships.",
        "scale_map",
    ),
    Lens(
        "cost_transfer",
        "consequence",
        "Preserve success while transferring its cost to another dimension, participant, or timescale.",
        "Do not add unrelated tragedy.",
        "cost_graph",
    ),
    Lens(
        "recursive_consequence",
        "recursive",
        "Make the proposed solution recreate the original problem at a higher structural level.",
        "The recursion must arise from the solution itself.",
        "recursive_state_graph",
    ),
    Lens(
        "self_refutation",
        "belief",
        "Make success disprove the belief or premise that motivated the successful strategy.",
        "Do not rely on coincidence.",
        "belief_outcome_graph",
    ),
    Lens(
        "value_collision",
        "ethical",
        "Force two independently defensible values into genuine incompatibility.",
        "Do not make one side obviously fraudulent.",
        "value_conflict_graph",
    ),
    Lens(
        "symmetry_break",
        "structural",
        "Establish a strong structural symmetry and violate it at the point completion is expected.",
        "The broken symmetry must alter meaning or causality.",
        "symmetry_graph",
    ),
    Lens(
        "mundane_causality",
        "tone",
        "Replace the dramatic expected explanation with an ordinary mechanism whose implications are stronger.",
        "Do not reduce stakes merely for irony.",
        "causal_graph",
    ),
    Lens(
        "extreme_specificity",
        "specificity",
        "Replace generic motivation with one precise causal fact that reorganizes the problem.",
        "Specificity must change structure, not decoration.",
        "specificity_map",
    ),
    Lens(
        "hostile_reading",
        "adversarial",
        "Interpret every convenient assumption in the least charitable internally consistent way.",
        "Do not violate established facts.",
        "falsification_tree",
    ),
    Lens(
        "genre_mechanism_attack",
        "anti_cliche",
        "Identify the most genre-typical mechanism and construct an alternative without that mechanism.",
        "Do not merely rename genre conventions.",
        "genre_mechanism_graph",
    ),
    Lens(
        "first_answer_rejection",
        "anti_cliche",
        "Assume the first plausible solution is contaminated by familiarity and search one structural layer deeper.",
        "Do not reward obscurity for its own sake.",
        "solution_depth_tree",
    ),
    Lens(
        "predictability_attack",
        "anti_cliche",
        "Model the likely audience or operator prediction and invalidate its causal basis fairly.",
        "Do not withhold required information.",
        "prediction_graph",
    ),
    Lens(
        "trope_decomposition",
        "anti_cliche",
        "Decompose the apparent trope into mechanism, expectation, payoff, and emotional function, then replace only its mechanism.",
        "Preserve any useful function the trope was serving.",
        "trope_component_graph",
    ),
    Lens(
        "cliche_completion_refusal",
        "anti_cliche",
        "Identify the conventional completion pattern and stop it before the expected payoff, then make that interruption meaningful.",
        "Do not confuse incompletion with subversion.",
        "completion_state_machine",
    ),
    Lens(
        "anti_twist",
        "anti_cliche",
        "Reject the assumption that surprise requires concealed information and derive surprise from visible facts.",
        "No arbitrary secret reveal.",
        "visible_fact_graph",
    ),
    Lens(
        "second_order_subversion",
        "anti_cliche",
        "Assume the obvious subversion has itself become conventional and invert the expectation created by that subversion.",
        "Do not restore the original cliché unchanged.",
        "expectation_stack",
    ),
    Lens(
        "constraint_collision",
        "constraint",
        "Force two hard constraints to interact until a third possibility emerges from their collision.",
        "Neither constraint may be discarded.",
        "constraint_interference_graph",
    ),
    Lens(
        "resource_reversal",
        "resource",
        "Treat the apparent resource as the limiting liability and the apparent limitation as the useful resource.",
        "The reversal must follow actual properties.",
        "resource_graph",
    ),
)


def composition_pairs(
    count: int,
) -> list[tuple[Lens, Lens]]:
    output = []
    total = len(lenses)

    for index in range(total):
        first = lenses[index]

        second = lenses[
            (index * 11 + 7) % total
        ]

        if first.id == second.id:
            second = lenses[
                (index + 1) % total
            ]

        output.append(
            (first, second)
        )

        if len(output) >= count:
            break

    return output


def diversity_signature(
    selected: list[Lens],
) -> dict[str, Any]:
    families = sorted(
        {
            lens.family
            for lens in selected
        }
    )

    representations = sorted(
        {
            lens.representation
            for lens in selected
        }
    )

    return {
        "family_count": len(
            families
        ),
        "families": families,
        "representation_count": len(
            representations
        ),
        "representations": (
            representations
        ),
    }


class DivergenceCompiler:
    def compile(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
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

        context = str(
            payload.get(
                "context",
                "",
            )
        ).strip()

        baselines = normalize_strings(
            payload.get(
                "baselines",
                [],
            )
        )

        cliches = normalize_strings(
            payload.get(
                "cliches",
                [],
            )
        )

        constraints_raw = payload.get(
            "constraints",
            {},
        )

        if not isinstance(
            constraints_raw,
            dict,
        ):
            constraints_raw = {}

        required = normalize_strings(
            constraints_raw.get(
                "required",
                [],
            )
        )

        forbidden = normalize_strings(
            constraints_raw.get(
                "forbidden",
                [],
            )
        )

        requested_count = int(
            payload.get(
                "candidate_count",
                16,
            )
        )

        candidate_count = max(
            4,
            min(
                requested_count,
                32,
            ),
        )

        single_count = min(
            candidate_count,
            len(lenses),
        )

        selected = list(
            lenses[:single_count]
        )

        packets = []

        for index, lens in enumerate(
            selected
        ):
            packet_identity = {
                "subject": subject,
                "lens": lens.id,
                "index": index,
                "constraints": {
                    "required": required,
                    "forbidden": forbidden,
                },
            }

            packets.append(
                {
                    "instance_id": stable_id(
                        "instance",
                        packet_identity,
                    ),
                    "owner": "underscore",
                    "kind": (
                        "divergent_candidate_assignment"
                    ),
                    "generation": 0,
                    "lens": asdict(
                        lens
                    ),
                    "subject": subject,
                    "context": context,
                    "baselines": baselines,
                    "cliches": cliches,
                    "constraints": {
                        "required": required,
                        "forbidden": forbidden,
                    },
                    "instruction": (
                        "Produce one concrete candidate "
                        "that satisfies the objective of "
                        f"the {lens.id} lens. "
                        f"{lens.objective} "
                        f"Constraint: {lens.prohibition} "
                        "Preserve supplied facts and hard "
                        "constraints. Do not optimize for "
                        "novelty alone. State the causal "
                        "or structural difference from the "
                        "baseline explicitly."
                    ),
                    "expected_output": {
                        "text": "string",
                        "difference": "string",
                        "assumptions": "list",
                        "constraint_notes": (
                            "list"
                        ),
                    },
                    "authority_effect": (
                        authority_effect
                    ),
                }
            )

        remaining = (
            candidate_count
            - len(packets)
        )

        if remaining > 0:
            pairs = composition_pairs(
                remaining
            )

            for offset, (
                first,
                second,
            ) in enumerate(pairs):
                index = len(
                    packets
                )

                identity = {
                    "subject": subject,
                    "lenses": [
                        first.id,
                        second.id,
                    ],
                    "index": index,
                    "constraints": {
                        "required": required,
                        "forbidden": forbidden,
                    },
                }

                packets.append(
                    {
                        "instance_id": stable_id(
                            "instance",
                            identity,
                        ),
                        "owner": (
                            "underscore"
                        ),
                        "kind": (
                            "divergent_candidate_assignment"
                        ),
                        "generation": 0,
                        "lens": {
                            "id": (
                                first.id
                                + "+"
                                + second.id
                            ),
                            "family": (
                                first.family
                                + "+"
                                + second.family
                            ),
                            "objective": (
                                first.objective
                                + " Then apply a second "
                                "independent transformation: "
                                + second.objective
                            ),
                            "prohibition": (
                                first.prohibition
                                + " "
                                + second.prohibition
                            ),
                            "representation": (
                                first.representation
                                + "+"
                                + second.representation
                            ),
                        },
                        "subject": subject,
                        "context": context,
                        "baselines": baselines,
                        "cliches": cliches,
                        "constraints": {
                            "required": required,
                            "forbidden": forbidden,
                        },
                        "instruction": (
                            "Produce one concrete candidate "
                            "by composing two independent "
                            "divergence operations. First: "
                            f"{first.objective} "
                            "Second: "
                            f"{second.objective} "
                            "Preserve supplied facts and "
                            "hard constraints. The second "
                            "operation must materially change "
                            "the first result rather than "
                            "decorate it."
                        ),
                        "expected_output": {
                            "text": "string",
                            "difference": (
                                "string"
                            ),
                            "assumptions": "list",
                            "constraint_notes": (
                                "list"
                            ),
                        },
                        "authority_effect": (
                            authority_effect
                        ),
                    }
                )

        segue_packets = []

        for packet in packets:
            segue_payload = {
                "source_instance_id": (
                    packet[
                        "instance_id"
                    ]
                ),
                "target": (
                    "underscore."
                    "divergence.realization"
                ),
                "lens": packet[
                    "lens"
                ],
                "instruction": (
                    packet[
                        "instruction"
                    ]
                ),
                "expected_output": (
                    packet[
                        "expected_output"
                    ]
                ),
            }

            segue_packets.append(
                {
                    "segue_id": stable_id(
                        "segue",
                        segue_payload,
                    ),
                    "segue_type": (
                        "underscore.divergence."
                        "assignment_to_realization"
                    ),
                    "owner": "underscore",
                    "source_instance_id": (
                        packet[
                            "instance_id"
                        ]
                    ),
                    "target": (
                        "underscore."
                        "divergence.realization"
                    ),
                    "authority_effect": (
                        authority_effect
                    ),
                    "payload": (
                        segue_payload
                    ),
                }
            )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "capability": (
                "divergence_compiler"
            ),
            "authority_effect": (
                authority_effect
            ),
            "subject": subject,
            "candidate_count": len(
                packets
            ),
            "candidate_assignments": (
                packets
            ),
            "segues": segue_packets,
            "diversity": (
                diversity_signature(
                    selected
                )
            ),
            "invariants": {
                "projection_only": True,
                "assignments_are_not_answers": True,
                "assignments_are_not_authority": True,
                "hard_constraints_preserved": True,
                "novelty_alone_cannot_win": True,
                "source_subject_preserved": True,
                "realization_is_external": True,
                "vessel_selection_occurs_after_realization": True,
                "candidate_identity_deterministic": True,
                "segue_identity_deterministic": True,
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
                "context": context,
                "baselines": baselines,
                "cliches": cliches,
                "constraints": {
                    "required": (
                        required
                    ),
                    "forbidden": (
                        forbidden
                    ),
                },
                "candidate_assignments": (
                    packets
                ),
            }
        )

        return result


def self_check() -> dict[str, Any]:
    compiler = (
        DivergenceCompiler()
    )

    payload = {
        "subject": (
            "end a story without using "
            "a conventional surprise twist"
        ),
        "context": (
            "The ending must be earned "
            "by already-visible facts."
        ),
        "baselines": [
            (
                "a hidden fact is revealed "
                "at the final moment"
            )
        ],
        "cliches": [
            "it was all a dream",
            "secret identity reveal",
            "last-second rescue",
        ],
        "constraints": {
            "required": [
                "earned",
            ],
            "forbidden": [
                "dream",
            ],
        },
        "candidate_count": 20,
    }

    first = compiler.compile(
        payload
    )

    second = compiler.compile(
        payload
    )

    if (
        first["fingerprint"]
        != second["fingerprint"]
    ):
        raise RuntimeError(
            "determinism check failed"
        )

    if (
        first[
            "candidate_count"
        ]
        != 20
    ):
        raise RuntimeError(
            "candidate count failed"
        )

    if len(
        first["segues"]
    ) != 20:
        raise RuntimeError(
            "segue count failed"
        )

    instance_ids = {
        item["instance_id"]
        for item
        in first[
            "candidate_assignments"
        ]
    }

    if len(
        instance_ids
    ) != 20:
        raise RuntimeError(
            "candidate identity "
            "uniqueness failed"
        )

    segue_ids = {
        item["segue_id"]
        for item
        in first["segues"]
    }

    if len(
        segue_ids
    ) != 20:
        raise RuntimeError(
            "segue identity "
            "uniqueness failed"
        )

    if any(
        item[
            "authority_effect"
        ]
        != "none"
        for item
        in first[
            "candidate_assignments"
        ]
    ):
        raise RuntimeError(
            "candidate authority "
            "invariant failed"
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
            first[
                "candidate_count"
            ]
        ),
        "segue_count": len(
            first["segues"]
        ),
        "family_count": (
            first[
                "diversity"
            ][
                "family_count"
            ]
        ),
        "representation_count": (
            first[
                "diversity"
            ][
                "representation_count"
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
            "underscore-divergence-compiler"
        ),
        description=(
            "compile deterministic "
            "underscore divergent "
            "candidate assignments"
        ),
    )

    commands = (
        parser.add_subparsers(
            dest="command",
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
        help=(
            "JSON input path or -"
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

    compiler = (
        DivergenceCompiler()
    )

    if args.command == (
        "compile"
    ):
        result = (
            compiler.compile(
                load_payload(
                    args.input
                )
            )
        )

    elif args.command == (
        "self-check"
    ):
        result = (
            self_check()
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
