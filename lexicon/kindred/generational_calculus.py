#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from role_calculus import (
    KindredRoleError,
    Qualification,
    RoleProfile,
    SexMarker,
    ascending_role,
    descending_role,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GenerationalStep:
    source: str
    target: str
    segue_id: str
    qualification: Qualification | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise KindredRoleError(
                "generational step source is required"
            )

        if not self.target.strip():
            raise KindredRoleError(
                "generational step target is required"
            )

        if self.source == self.target:
            raise KindredRoleError(
                "generational step cannot be self-referential"
            )

        if not self.segue_id.strip():
            raise KindredRoleError(
                "generational step segue_id is required"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class GenerationalDerivation:
    source: str
    target: str
    source_role: RoleProfile
    target_role: RoleProfile
    generation_distance: int
    path: tuple[GenerationalStep, ...]
    qualifications: tuple[Qualification, ...]
    homogeneous_qualification: Qualification | None
    evidence_complete: bool

    def __post_init__(self) -> None:
        if self.generation_distance < 2:
            raise KindredRoleError(
                "generational derivation requires "
                "distance of at least two"
            )

        if len(self.path) != self.generation_distance:
            raise KindredRoleError(
                "generation distance does not match path"
            )

        if self.path[0].source != self.source:
            raise KindredRoleError(
                "path does not begin at source"
            )

        if self.path[-1].target != self.target:
            raise KindredRoleError(
                "path does not terminate at target"
            )

        previous = self.source

        for step in self.path:
            if step.source != previous:
                raise KindredRoleError(
                    "generational path is discontinuous"
                )

            previous = step.target

    def certificate(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "source_role": self.source_role.role_id,
            "target_role": self.target_role.role_id,
            "generation_distance":
                self.generation_distance,
            "path": [
                {
                    "source": step.source,
                    "target": step.target,
                    "segue_id": step.segue_id,
                    "qualification": (
                        step.qualification.value
                        if step.qualification is not None
                        else None
                    ),
                }
                for step in self.path
            ],
            "qualifications": [
                qualification.value
                for qualification in self.qualifications
            ],
            "homogeneous_qualification": (
                self.homogeneous_qualification.value
                if self.homogeneous_qualification is not None
                else None
            ),
            "evidence_complete":
                self.evidence_complete,
            "authoritative":
                False,
            "projection":
                "kindred_generational_derivation",
        }


def _normalize_path(
    path: Iterable[GenerationalStep],
) -> tuple[GenerationalStep, ...]:
    normalized = tuple(path)

    if len(normalized) < 2:
        raise KindredRoleError(
            "grandmother grandfather granddaughter "
            "or grandson derivation requires at least "
            "two direct descent steps"
        )

    return normalized


def _homogeneous_qualification(
    path: tuple[GenerationalStep, ...],
) -> Qualification | None:
    values = {
        step.qualification
        for step in path
        if step.qualification is not None
    }

    if len(values) != 1:
        return None

    if any(
        step.qualification is None
        for step in path
    ):
        return None

    return next(iter(values))


def derive_generational_roles(
    *,
    source: str,
    target: str,
    source_sex: SexMarker,
    target_sex: SexMarker,
    path: Iterable[GenerationalStep],
    evidence_complete: bool = True,
) -> GenerationalDerivation:
    normalized = _normalize_path(
        path
    )

    if normalized[0].source != source:
        raise KindredRoleError(
            "source does not match first path step"
        )

    if normalized[-1].target != target:
        raise KindredRoleError(
            "target does not match final path step"
        )

    previous = source

    for step in normalized:
        if step.source != previous:
            raise KindredRoleError(
                "generational path is discontinuous"
            )

        previous = step.target

    distance = len(normalized)

    homogeneous = _homogeneous_qualification(
        normalized
    )

    source_role = ascending_role(
        source_sex,
        distance,
        homogeneous,
    )

    target_role = descending_role(
        target_sex,
        distance,
        homogeneous,
    )

    qualifications = tuple(
        step.qualification
        for step in normalized
        if step.qualification is not None
    )

    return GenerationalDerivation(
        source=source,
        target=target,
        source_role=source_role,
        target_role=target_role,
        generation_distance=distance,
        path=normalized,
        qualifications=qualifications,
        homogeneous_qualification=homogeneous,
        evidence_complete=evidence_complete,
    )


def derive_grand_roles(
    *,
    source: str,
    target: str,
    source_sex: SexMarker,
    target_sex: SexMarker,
    first_step: GenerationalStep,
    second_step: GenerationalStep,
    evidence_complete: bool = True,
) -> GenerationalDerivation:
    return derive_generational_roles(
        source=source,
        target=target,
        source_sex=source_sex,
        target_sex=target_sex,
        path=(
            first_step,
            second_step,
        ),
        evidence_complete=evidence_complete,
    )


def enhancements() -> tuple[str, ...]:
    return (
        "grandmother_projection",
        "grandfather_projection",
        "granddaughter_projection",
        "grandson_projection",
        "symmetric_grand_role_projection",
        "unbounded_great_generation_projection",
        "generation_distance_tracking",
        "exact_descent_path_certificate",
        "segue_level_path_provenance",
        "path_continuity_validation",
        "qualification_path_preservation",
        "homogeneous_qualification_projection",
        "mixed_qualification_preservation",
        "immutable_generational_derivation",
        "non_authoritative_derived_roles",
        "single_authoritative_descent_storage",
        "deterministic_inverse_generation_roles",
        "evidence_completeness_tracking",
        "stable_specific_role_projection",
        "composition_over_duplication",
    )


def health() -> dict[str, object]:
    return {
        "healthy": True,
        "minimum_generation_distance": 2,
        "unbounded_generation_distance": True,
        "specific_roles": [
            "grandmother",
            "grandfather",
            "granddaughter",
            "grandson",
        ],
        "generic_family_roles_canonical": False,
        "enhancement_count": len(
            enhancements()
        ),
    }
