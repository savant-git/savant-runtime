#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-experiment/1.0.0"
)

OWNER = "exile:envoy"
EXECUTION_OWNER = "exile:opus"
VERIFICATION_OWNER = "exile:notary"


class TraitExperimentError(
    ValueError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
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


def normalize_term(
    value: Any,
) -> str:
    return (
        str(
            value
            or ""
        )
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                normalized
                for value in values
                if (
                    normalized
                    := normalize_term(
                        value
                    )
                )
            }
        )
    )


def normalize_positive_int(
    value: Any,
    name: str,
) -> int:
    try:
        result = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise TraitExperimentError(
            f"{name} must be integer"
        ) from exc

    if result < 1:
        raise TraitExperimentError(
            f"{name} must be positive"
        )

    return result


@dataclass(
    frozen=True,
    slots=True,
)
class EvaluationDimension:
    dimension_id: str
    description: str
    weight: float = 1.0

    def __post_init__(
        self,
    ) -> None:
        identity = normalize_term(
            self.dimension_id
        )

        description = str(
            self.description
            or ""
        ).strip()

        try:
            weight = float(
                self.weight
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise TraitExperimentError(
                "dimension weight "
                "must be numeric"
            ) from exc

        if not identity:
            raise TraitExperimentError(
                "dimension_id is required"
            )

        if not description:
            raise TraitExperimentError(
                "dimension description "
                "is required"
            )

        if weight <= 0:
            raise TraitExperimentError(
                "dimension weight "
                "must be positive"
            )

        object.__setattr__(
            self,
            "dimension_id",
            identity,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "weight",
            weight,
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "dimension_id": (
                self.dimension_id
            ),
            "description": (
                self.description
            ),
            "weight": self.weight,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class EvaluationTask:
    task_id: str
    prompt: str
    domains: tuple[str, ...]
    target_traits: tuple[str, ...]
    dimensions: tuple[
        EvaluationDimension,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        task_id = normalize_term(
            self.task_id
        )

        prompt = str(
            self.prompt
            or ""
        ).strip()

        if not task_id:
            raise TraitExperimentError(
                "task_id is required"
            )

        if not prompt:
            raise TraitExperimentError(
                "task prompt is required"
            )

        if not self.dimensions:
            raise TraitExperimentError(
                "evaluation task requires "
                "at least one dimension"
            )

        ordered_dimensions = tuple(
            sorted(
                self.dimensions,
                key=lambda value: (
                    value.dimension_id
                ),
            )
        )

        dimension_ids = [
            value.dimension_id
            for value
            in ordered_dimensions
        ]

        if (
            len(
                dimension_ids
            )
            != len(
                set(
                    dimension_ids
                )
            )
        ):
            raise TraitExperimentError(
                "evaluation dimensions "
                "must be unique"
            )

        object.__setattr__(
            self,
            "task_id",
            task_id,
        )

        object.__setattr__(
            self,
            "prompt",
            prompt,
        )

        object.__setattr__(
            self,
            "domains",
            normalize_terms(
                self.domains
            ),
        )

        object.__setattr__(
            self,
            "target_traits",
            normalize_terms(
                self.target_traits
            ),
        )

        object.__setattr__(
            self,
            "dimensions",
            ordered_dimensions,
        )

    @property
    def task_digest(
        self,
    ) -> str:
        return digest(
            self.projection()
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "domains": list(
                self.domains
            ),
            "target_traits": list(
                self.target_traits
            ),
            "dimensions": [
                dimension.projection()
                for dimension
                in self.dimensions
            ],
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ExperimentParticipant:
    participant_id: str
    provider_id: str
    model_id: str
    model_version: str = ""

    def __post_init__(
        self,
    ) -> None:
        participant_id = (
            normalize_term(
                self.participant_id
            )
        )

        provider_id = normalize_term(
            self.provider_id
        )

        model_id = str(
            self.model_id
            or ""
        ).strip()

        model_version = str(
            self.model_version
            or ""
        ).strip()

        if not participant_id:
            raise TraitExperimentError(
                "participant_id "
                "is required"
            )

        if not provider_id:
            raise TraitExperimentError(
                "provider_id is required"
            )

        if not model_id:
            raise TraitExperimentError(
                "model_id is required"
            )

        object.__setattr__(
            self,
            "participant_id",
            participant_id,
        )

        object.__setattr__(
            self,
            "provider_id",
            provider_id,
        )

        object.__setattr__(
            self,
            "model_id",
            model_id,
        )

        object.__setattr__(
            self,
            "model_version",
            model_version,
        )

    @property
    def blind_id(
        self,
    ) -> str:
        material = {
            "participant_id": (
                self.participant_id
            ),
            "provider_id": (
                self.provider_id
            ),
            "model_id": (
                self.model_id
            ),
            "model_version": (
                self.model_version
            ),
        }

        return (
            "participant:"
            + digest(
                material
            )[:16]
        )

    def execution_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "participant_id": (
                self.participant_id
            ),
            "provider_id": (
                self.provider_id
            ),
            "model_id": (
                self.model_id
            ),
            "model_version": (
                self.model_version
            ),
            "blind_id": (
                self.blind_id
            ),
            "execution_owner": (
                EXECUTION_OWNER
            ),
        }

    def blind_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "blind_id": self.blind_id,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ExperimentPlan:
    experiment_id: str
    trait_ids: tuple[str, ...]
    tasks: tuple[
        EvaluationTask,
        ...,
    ]
    participants: tuple[
        ExperimentParticipant,
        ...,
    ]
    repetitions: int = 3

    def __post_init__(
        self,
    ) -> None:
        experiment_id = (
            normalize_term(
                self.experiment_id
            )
        )

        if not experiment_id:
            raise TraitExperimentError(
                "experiment_id "
                "is required"
            )

        if not self.tasks:
            raise TraitExperimentError(
                "experiment requires "
                "at least one task"
            )

        if not self.participants:
            raise TraitExperimentError(
                "experiment requires "
                "at least one participant"
            )

        repetitions = (
            normalize_positive_int(
                self.repetitions,
                "repetitions",
            )
        )

        tasks = tuple(
            sorted(
                self.tasks,
                key=lambda value: (
                    value.task_id
                ),
            )
        )

        participants = tuple(
            sorted(
                self.participants,
                key=lambda value: (
                    value.blind_id
                ),
            )
        )

        task_ids = [
            value.task_id
            for value
            in tasks
        ]

        if (
            len(
                task_ids
            )
            != len(
                set(
                    task_ids
                )
            )
        ):
            raise TraitExperimentError(
                "task ids must be unique"
            )

        blind_ids = [
            value.blind_id
            for value
            in participants
        ]

        if (
            len(
                blind_ids
            )
            != len(
                set(
                    blind_ids
                )
            )
        ):
            raise TraitExperimentError(
                "participant identities "
                "must be unique"
            )

        object.__setattr__(
            self,
            "experiment_id",
            experiment_id,
        )

        object.__setattr__(
            self,
            "trait_ids",
            normalize_terms(
                self.trait_ids
            ),
        )

        object.__setattr__(
            self,
            "tasks",
            tasks,
        )

        object.__setattr__(
            self,
            "participants",
            participants,
        )

        object.__setattr__(
            self,
            "repetitions",
            repetitions,
        )

    @property
    def plan_id(
        self,
    ) -> str:
        return (
            "trait-experiment:"
            + digest(
                self.projection(
                    blinded=False
                )
            )[:32]
        )

    def projection(
        self,
        *,
        blinded: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "experiment_id": (
                self.experiment_id
            ),
            "trait_ids": list(
                self.trait_ids
            ),
            "tasks": [
                task.projection()
                for task
                in self.tasks
            ],
            "participants": [
                (
                    participant
                    .blind_projection()
                    if blinded
                    else participant
                    .execution_projection()
                )
                for participant
                in self.participants
            ],
            "repetitions": (
                self.repetitions
            ),
            "blind_evaluation": True,
            "identical_task_packets": True,
            "provider_identity_role": (
                "execution_provenance_only"
            ),
            "execution_owner": (
                EXECUTION_OWNER
            ),
            "evaluation_owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def execution_packets(
        self,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        packets: list[
            dict[str, Any]
        ] = []

        for repetition in range(
            1,
            self.repetitions + 1,
        ):
            for task in self.tasks:
                for participant in (
                    self.participants
                ):
                    material = {
                        "experiment_id": (
                            self.experiment_id
                        ),
                        "plan_id": (
                            self.plan_id
                        ),
                        "repetition": (
                            repetition
                        ),
                        "task": (
                            task.projection()
                        ),
                        "participant": (
                            participant
                            .execution_projection()
                        ),
                    }

                    packet_id = (
                        "experiment-run:"
                        + digest(
                            material
                        )[:32]
                    )

                    packets.append(
                        {
                            "packet_id": (
                                packet_id
                            ),
                            **material,
                            "execution_owner": (
                                EXECUTION_OWNER
                            ),
                            "evaluation_owner": (
                                OWNER
                            ),
                            "authoritative": (
                                False
                            ),
                            "authority_effect": (
                                "none"
                            ),
                        }
                    )

        return tuple(
            packets
        )


@dataclass(
    frozen=True,
    slots=True,
)
class BlindResult:
    packet_id: str
    blind_id: str
    output_text: str
    response_id: str = ""

    def __post_init__(
        self,
    ) -> None:
        packet_id = str(
            self.packet_id
            or ""
        ).strip()

        blind_id = str(
            self.blind_id
            or ""
        ).strip()

        output_text = str(
            self.output_text
            or ""
        )

        response_id = str(
            self.response_id
            or ""
        ).strip()

        if not packet_id:
            raise TraitExperimentError(
                "packet_id is required"
            )

        if not blind_id:
            raise TraitExperimentError(
                "blind_id is required"
            )

        if not output_text.strip():
            raise TraitExperimentError(
                "output_text is required"
            )

        object.__setattr__(
            self,
            "packet_id",
            packet_id,
        )

        object.__setattr__(
            self,
            "blind_id",
            blind_id,
        )

        object.__setattr__(
            self,
            "output_text",
            output_text,
        )

        object.__setattr__(
            self,
            "response_id",
            response_id,
        )

    @property
    def result_id(
        self,
    ) -> str:
        return (
            "blind-result:"
            + digest(
                self.projection()
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "packet_id": (
                self.packet_id
            ),
            "blind_id": (
                self.blind_id
            ),
            "output_text": (
                self.output_text
            ),
            "response_id": (
                self.response_id
            ),
            "provider_identity_exposed": (
                False
            ),
            "evaluation_owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "authoritative": False,
            "authority_effect": "none",
        }


def default_dimensions() -> tuple[
    EvaluationDimension,
    ...,
]:
    return (
        EvaluationDimension(
            dimension_id="correctness",
            description=(
                "Degree to which the response "
                "is substantively correct."
            ),
            weight=1.0,
        ),
        EvaluationDimension(
            dimension_id=(
                "instruction_adherence"
            ),
            description=(
                "Degree to which the response "
                "satisfies explicit task "
                "constraints."
            ),
            weight=1.0,
        ),
        EvaluationDimension(
            dimension_id=(
                "evidence_discipline"
            ),
            description=(
                "Degree to which claims are "
                "properly separated from "
                "inference and unsupported "
                "assertion."
            ),
            weight=1.0,
        ),
        EvaluationDimension(
            dimension_id=(
                "internal_consistency"
            ),
            description=(
                "Degree to which the response "
                "remains logically and "
                "semantically consistent."
            ),
            weight=1.0,
        ),
    )


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-experiment-status/"
            "1.0.0"
        ),
        "owner": OWNER,
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "verification_owner": (
            VERIFICATION_OWNER
        ),
        "identical_task_packets": True,
        "blind_evaluation": True,
        "repeated_trials": True,
        "deterministic_packet_identity": (
            True
        ),
        "provider_identity_role": (
            "execution_provenance_only"
        ),
        "automatic_champion_selection": (
            False
        ),
        "automatic_evidence_admission": (
            False
        ),
        "baseline_mutation": False,
        "crown_mutation": False,
        "persistent_store": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def main() -> int:
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
