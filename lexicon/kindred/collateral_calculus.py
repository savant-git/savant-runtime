#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from role_calculus import (
    KindredRoleError,
    Qualification,
    RoleProfile,
    SexMarker,
    aunt_uncle_role,
    niece_nephew_role,
)


@dataclass(
    frozen=True,
    slots=True,
)
class CollateralStep:
    source: str
    target: str
    relationship_role: RoleProfile
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise KindredRoleError(
                "collateral step source is required"
            )

        if not self.target.strip():
            raise KindredRoleError(
                "collateral step target is required"
            )

        if self.source == self.target:
            raise KindredRoleError(
                "collateral step endpoints must differ"
            )

        if not self.evidence_ids:
            raise KindredRoleError(
                "collateral step requires evidence"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AuntNieceDerivation:
    ascending_instance: str
    descending_instance: str
    ascending_role: RoleProfile
    descending_role: RoleProfile
    collateral_step: CollateralStep
    descent_path: tuple[str, ...]
    generation_distance: int
    qualification: Qualification | None
    evidence_ids: tuple[str, ...]
    evidence_complete: bool

    def __post_init__(self) -> None:
        if self.generation_distance < 1:
            raise KindredRoleError(
                "collateral generation distance "
                "must be positive"
            )

        if not self.descent_path:
            raise KindredRoleError(
                "descent path is required"
            )

        if len(
            self.descent_path
        ) != self.generation_distance:
            raise KindredRoleError(
                "descent path length does not match "
                "generation distance"
            )

        if not self.evidence_ids:
            raise KindredRoleError(
                "derivation requires evidence"
            )

    def certificate(self) -> dict[str, object]:
        return {
            "ascending_instance":
                self.ascending_instance,
            "descending_instance":
                self.descending_instance,
            "ascending_role":
                self.ascending_role.role_id,
            "descending_role":
                self.descending_role.role_id,
            "generation_distance":
                self.generation_distance,
            "qualification": (
                self.qualification.value
                if self.qualification is not None
                else None
            ),
            "collateral_step": {
                "source":
                    self.collateral_step.source,
                "target":
                    self.collateral_step.target,
                "relationship_role":
                    self.collateral_step
                    .relationship_role
                    .role_id,
                "evidence_ids":
                    list(
                        self.collateral_step
                        .evidence_ids
                    ),
            },
            "descent_path":
                list(self.descent_path),
            "evidence_ids":
                list(self.evidence_ids),
            "evidence_complete":
                self.evidence_complete,
            "authoritative":
                False,
            "projection":
                "kindred_aunt_niece_derivation",
        }


def _normalize_ids(
    values: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
    )


def derive_aunt_uncle_niece_nephew(
    *,
    ascending_instance: str,
    descending_instance: str,
    ascending_sex: SexMarker,
    descending_sex: SexMarker,
    collateral_source: str,
    collateral_target: str,
    collateral_role: RoleProfile,
    collateral_evidence_ids: Iterable[str],
    descent_path: Iterable[str],
    descent_evidence_ids: Iterable[str],
    evidence_complete: bool = True,
) -> AuntNieceDerivation:
    ascending_instance = (
        ascending_instance.strip()
    )
    descending_instance = (
        descending_instance.strip()
    )

    if not ascending_instance:
        raise KindredRoleError(
            "ascending instance is required"
        )

    if not descending_instance:
        raise KindredRoleError(
            "descending instance is required"
        )

    if (
        ascending_instance
        == descending_instance
    ):
        raise KindredRoleError(
            "derived relationship endpoints "
            "must differ"
        )

    if collateral_role.axis.value != "collateral":
        raise KindredRoleError(
            "collateral role must use "
            "collateral axis"
        )

    collateral_evidence = _normalize_ids(
        collateral_evidence_ids
    )

    descent_evidence = _normalize_ids(
        descent_evidence_ids
    )

    normalized_path = tuple(
        str(value).strip()
        for value in descent_path
        if str(value).strip()
    )

    if not normalized_path:
        raise KindredRoleError(
            "descent path requires at least "
            "one authoritative Segue"
        )

    if not collateral_evidence:
        raise KindredRoleError(
            "collateral derivation evidence "
            "is required"
        )

    if not descent_evidence:
        raise KindredRoleError(
            "descent evidence is required"
        )

    qualification = (
        collateral_role.qualification
        if collateral_role.qualification
        in {
            Qualification.FULL,
            Qualification.HALF,
            Qualification.ADOPTIVE,
            Qualification.STEP,
        }
        else None
    )

    generations = len(
        normalized_path
    )

    ascending_role = aunt_uncle_role(
        ascending_sex,
        generations_above=generations,
        qualification=qualification,
    )

    descending_role = niece_nephew_role(
        descending_sex,
        generations_below=generations,
        qualification=qualification,
    )

    collateral_step = CollateralStep(
        source=collateral_source,
        target=collateral_target,
        relationship_role=collateral_role,
        evidence_ids=collateral_evidence,
    )

    all_evidence = _normalize_ids(
        (
            *collateral_evidence,
            *descent_evidence,
        )
    )

    return AuntNieceDerivation(
        ascending_instance=
            ascending_instance,
        descending_instance=
            descending_instance,
        ascending_role=ascending_role,
        descending_role=descending_role,
        collateral_step=collateral_step,
        descent_path=normalized_path,
        generation_distance=generations,
        qualification=qualification,
        evidence_ids=all_evidence,
        evidence_complete=evidence_complete,
    )


def enhancements() -> tuple[str, ...]:
    return (
        "aunt_projection",
        "uncle_projection",
        "niece_projection",
        "nephew_projection",
        "sex_specific_collateral_roles",
        "symmetric_inverse_collateral_roles",
        "great_aunt_projection",
        "great_uncle_projection",
        "great_niece_projection",
        "great_nephew_projection",
        "unbounded_collateral_generation_depth",
        "full_collateral_qualification",
        "half_collateral_qualification",
        "adoptive_collateral_qualification",
        "step_collateral_qualification",
        "collateral_evidence_certificate",
        "descent_evidence_certificate",
        "combined_evidence_provenance",
        "immutable_collateral_derivation",
        "non_authoritative_collateral_projection",
        "no_duplicate_collateral_authority",
        "explicit_generation_distance",
        "evidence_completeness_tracking",
        "specific_role_only_projection",
        "qualification_preservation",
    )


def health() -> dict[str, object]:
    return {
        "healthy": True,
        "specific_roles": [
            "aunt",
            "uncle",
            "niece",
            "nephew",
        ],
        "unbounded_generation_depth": True,
        "generic_family_roles_canonical": False,
        "enhancement_count":
            len(enhancements()),
    }
