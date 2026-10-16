#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Final


class KindredRoleError(ValueError):
    pass


class SexMarker(str, Enum):
    FEMALE = "female"
    MALE = "male"


class Axis(str, Enum):
    DESCENT = "descent"
    COLLATERAL = "collateral"
    ALLIANCE = "alliance"
    AFFINITY = "affinity"
    GUARDIANSHIP = "guardianship"


class Qualification(str, Enum):
    BIOLOGICAL = "biological"
    ADOPTIVE = "adoptive"
    STEP = "step"
    FOSTER = "foster"
    LEGAL = "legal"
    GUARDIAN = "guardian"
    FULL = "full"
    HALF = "half"


@dataclass(
    frozen=True,
    slots=True,
)
class RoleProfile:
    role_id: str
    label: str
    sex: SexMarker
    axis: Axis
    ascent: int = 0
    descent: int = 0
    collateral: bool = False
    degree: int | None = None
    removal: int = 0
    qualification: Qualification | None = None
    reciprocal_role_id: str | None = None

    def __post_init__(self) -> None:
        if self.ascent < 0:
            raise KindredRoleError(
                "ascent cannot be negative"
            )

        if self.descent < 0:
            raise KindredRoleError(
                "descent cannot be negative"
            )

        if self.removal < 0:
            raise KindredRoleError(
                "removal cannot be negative"
            )

        if self.degree is not None and self.degree < 1:
            raise KindredRoleError(
                "cousin degree must be positive"
            )

        if self.ascent and self.descent:
            raise KindredRoleError(
                "a role cannot be simultaneously "
                "ascending and descending"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class LateralDerivation:
    first_role: RoleProfile
    second_role: RoleProfile
    qualification: Qualification
    shared_ascendant_count: int
    first_ascendants: tuple[str, ...]
    second_ascendants: tuple[str, ...]
    shared_ascendants: tuple[str, ...]
    evidence_complete: bool

    def __post_init__(self) -> None:
        if self.qualification not in {
            Qualification.FULL,
            Qualification.HALF,
        }:
            raise KindredRoleError(
                "lateral derivation requires "
                "full or half qualification"
            )

        if self.shared_ascendant_count < 1:
            raise KindredRoleError(
                "lateral derivation requires "
                "shared ascendant evidence"
            )

        if (
            self.shared_ascendant_count
            != len(self.shared_ascendants)
        ):
            raise KindredRoleError(
                "shared ascendant count mismatch"
            )

    def certificate(self) -> dict[str, object]:
        return {
            "first_role":
                self.first_role.role_id,
            "second_role":
                self.second_role.role_id,
            "qualification":
                self.qualification.value,
            "shared_ascendant_count":
                self.shared_ascendant_count,
            "first_ascendants":
                list(self.first_ascendants),
            "second_ascendants":
                list(self.second_ascendants),
            "shared_ascendants":
                list(self.shared_ascendants),
            "evidence_complete":
                self.evidence_complete,
            "authoritative":
                False,
            "projection":
                "kindred_lateral_derivation",
        }


FEMALE: Final = SexMarker.FEMALE
MALE: Final = SexMarker.MALE


def _sex_word(
    sex: SexMarker,
    female: str,
    male: str,
) -> str:
    return (
        female
        if sex is FEMALE
        else male
    )


def _ordinal(
    value: int,
) -> str:
    if value <= 0:
        raise KindredRoleError(
            "ordinal value must be positive"
        )

    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(
            value % 10,
            "th",
        )

    return f"{value}{suffix}"


def _great_prefix(
    count: int,
) -> str:
    if count <= 0:
        return ""

    return "great_" * count


def _qualification_prefix(
    qualification: Qualification | None,
) -> str:
    if qualification is None:
        return ""

    return f"{qualification.value}_"


def _normalized_ids(
    values: tuple[str, ...] | list[str] | set[str],
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


@lru_cache(maxsize=512)
def ascending_role(
    sex: SexMarker,
    generations: int,
    qualification: Qualification | None = None,
) -> RoleProfile:
    if generations < 1:
        raise KindredRoleError(
            "ascending generations must be positive"
        )

    prefix = _qualification_prefix(
        qualification
    )

    if generations == 1:
        noun = _sex_word(
            sex,
            "mother",
            "father",
        )
    elif generations == 2:
        noun = _sex_word(
            sex,
            "grandmother",
            "grandfather",
        )
    else:
        noun = (
            _great_prefix(
                generations - 2
            )
            + _sex_word(
                sex,
                "grandmother",
                "grandfather",
            )
        )

    label = prefix + noun

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.DESCENT,
        ascent=generations,
        qualification=qualification,
    )


@lru_cache(maxsize=512)
def descending_role(
    sex: SexMarker,
    generations: int,
    qualification: Qualification | None = None,
) -> RoleProfile:
    if generations < 1:
        raise KindredRoleError(
            "descending generations must be positive"
        )

    prefix = _qualification_prefix(
        qualification
    )

    if generations == 1:
        noun = _sex_word(
            sex,
            "daughter",
            "son",
        )
    elif generations == 2:
        noun = _sex_word(
            sex,
            "granddaughter",
            "grandson",
        )
    else:
        noun = (
            _great_prefix(
                generations - 2
            )
            + _sex_word(
                sex,
                "granddaughter",
                "grandson",
            )
        )

    label = prefix + noun

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.DESCENT,
        descent=generations,
        qualification=qualification,
    )


@lru_cache(maxsize=256)
def lateral_role(
    sex: SexMarker,
    qualification: Qualification | None = None,
) -> RoleProfile:
    prefix = _qualification_prefix(
        qualification
    )

    noun = _sex_word(
        sex,
        "sister",
        "brother",
    )

    label = prefix + noun

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.COLLATERAL,
        collateral=True,
        qualification=qualification,
    )


def derive_full_half(
    *,
    first_sex: SexMarker,
    second_sex: SexMarker,
    first_ascendants: tuple[str, ...] | list[str] | set[str],
    second_ascendants: tuple[str, ...] | list[str] | set[str],
    evidence_complete: bool = True,
) -> LateralDerivation:
    first = _normalized_ids(
        first_ascendants
    )
    second = _normalized_ids(
        second_ascendants
    )

    shared = tuple(
        sorted(
            set(first).intersection(
                second
            )
        )
    )

    if not shared:
        raise KindredRoleError(
            "cannot derive brother or sister "
            "without a shared qualifying ascendant"
        )

    if len(shared) == 1:
        qualification = Qualification.HALF

    elif (
        evidence_complete
        and set(first) == set(second)
    ):
        qualification = Qualification.FULL

    else:
        raise KindredRoleError(
            "full qualification requires complete "
            "evidence that the qualifying immediate "
            "ascendant sets are equal; otherwise "
            "qualification remains unresolved"
        )

    return LateralDerivation(
        first_role=lateral_role(
            first_sex,
            qualification,
        ),
        second_role=lateral_role(
            second_sex,
            qualification,
        ),
        qualification=qualification,
        shared_ascendant_count=len(
            shared
        ),
        first_ascendants=first,
        second_ascendants=second,
        shared_ascendants=shared,
        evidence_complete=evidence_complete,
    )


@lru_cache(maxsize=256)
def aunt_uncle_role(
    sex: SexMarker,
    generations_above: int = 1,
    qualification: Qualification | None = None,
) -> RoleProfile:
    if generations_above < 1:
        raise KindredRoleError(
            "generations_above must be positive"
        )

    prefix = _qualification_prefix(
        qualification
    )

    greats = _great_prefix(
        generations_above - 1
    )

    noun = _sex_word(
        sex,
        "aunt",
        "uncle",
    )

    label = prefix + greats + noun

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.COLLATERAL,
        ascent=generations_above,
        collateral=True,
        qualification=qualification,
    )


@lru_cache(maxsize=256)
def niece_nephew_role(
    sex: SexMarker,
    generations_below: int = 1,
    qualification: Qualification | None = None,
) -> RoleProfile:
    if generations_below < 1:
        raise KindredRoleError(
            "generations_below must be positive"
        )

    prefix = _qualification_prefix(
        qualification
    )

    greats = _great_prefix(
        generations_below - 1
    )

    noun = _sex_word(
        sex,
        "niece",
        "nephew",
    )

    label = prefix + greats + noun

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.COLLATERAL,
        descent=generations_below,
        collateral=True,
        qualification=qualification,
    )


@lru_cache(maxsize=2048)
def cousin_role(
    sex: SexMarker,
    degree: int,
    removal: int = 0,
    qualification: Qualification | None = None,
) -> RoleProfile:
    if degree < 1:
        raise KindredRoleError(
            "cousin degree must be positive"
        )

    if removal < 0:
        raise KindredRoleError(
            "cousin removal cannot be negative"
        )

    prefix = _qualification_prefix(
        qualification
    )

    label = (
        prefix
        + sex.value
        + "_"
        + _ordinal(degree)
        + "_cousin"
    )

    if removal:
        label += (
            "_"
            + str(removal)
            + "_time"
            + (
                "s"
                if removal != 1
                else ""
            )
            + "_removed"
        )

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.COLLATERAL,
        collateral=True,
        degree=degree,
        removal=removal,
        qualification=qualification,
    )


@lru_cache(maxsize=256)
def alliance_role(
    sex: SexMarker,
    *,
    former: bool = False,
) -> RoleProfile:
    noun = _sex_word(
        sex,
        "wife",
        "husband",
    )

    label = (
        f"former_{noun}"
        if former
        else noun
    )

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.ALLIANCE,
    )


@lru_cache(maxsize=256)
def guardian_role(
    sex: SexMarker,
) -> RoleProfile:
    label = (
        f"{sex.value}_guardian"
    )

    return RoleProfile(
        role_id=f"kindred.role.{label}",
        label=label,
        sex=sex,
        axis=Axis.GUARDIANSHIP,
        qualification=Qualification.GUARDIAN,
    )


@lru_cache(maxsize=256)
def affinity_ascending_role(
    sex: SexMarker,
    generations: int = 1,
) -> RoleProfile:
    if generations < 1:
        raise KindredRoleError(
            "generations must be positive"
        )

    if generations == 1:
        noun = _sex_word(
            sex,
            "mother_in_law",
            "father_in_law",
        )
    elif generations == 2:
        noun = _sex_word(
            sex,
            "grandmother_in_law",
            "grandfather_in_law",
        )
    else:
        noun = (
            _great_prefix(
                generations - 2
            )
            + _sex_word(
                sex,
                "grandmother_in_law",
                "grandfather_in_law",
            )
        )

    return RoleProfile(
        role_id=f"kindred.role.{noun}",
        label=noun,
        sex=sex,
        axis=Axis.AFFINITY,
        ascent=generations,
    )


@lru_cache(maxsize=256)
def affinity_descending_role(
    sex: SexMarker,
    generations: int = 1,
) -> RoleProfile:
    if generations < 1:
        raise KindredRoleError(
            "generations must be positive"
        )

    if generations == 1:
        noun = _sex_word(
            sex,
            "daughter_in_law",
            "son_in_law",
        )
    elif generations == 2:
        noun = _sex_word(
            sex,
            "granddaughter_in_law",
            "grandson_in_law",
        )
    else:
        noun = (
            _great_prefix(
                generations - 2
            )
            + _sex_word(
                sex,
                "granddaughter_in_law",
                "grandson_in_law",
            )
        )

    return RoleProfile(
        role_id=f"kindred.role.{noun}",
        label=noun,
        sex=sex,
        axis=Axis.AFFINITY,
        descent=generations,
    )


@lru_cache(maxsize=256)
def affinity_lateral_role(
    sex: SexMarker,
) -> RoleProfile:
    noun = _sex_word(
        sex,
        "sister_in_law",
        "brother_in_law",
    )

    return RoleProfile(
        role_id=f"kindred.role.{noun}",
        label=noun,
        sex=sex,
        axis=Axis.AFFINITY,
        collateral=True,
    )


def cousin_coordinates(
    first_distance: int,
    second_distance: int,
) -> tuple[int, int]:
    if first_distance < 2:
        raise KindredRoleError(
            "first common-ancestor distance "
            "must be at least two"
        )

    if second_distance < 2:
        raise KindredRoleError(
            "second common-ancestor distance "
            "must be at least two"
        )

    degree = (
        min(
            first_distance,
            second_distance,
        )
        - 1
    )

    removal = abs(
        first_distance
        - second_distance
    )

    return (
        degree,
        removal,
    )


def cousin_from_distances(
    sex: SexMarker,
    first_distance: int,
    second_distance: int,
) -> RoleProfile:
    degree, removal = cousin_coordinates(
        first_distance,
        second_distance,
    )

    return cousin_role(
        sex,
        degree,
        removal,
    )


def reciprocal_descent(
    source_sex: SexMarker,
    target_sex: SexMarker,
    generations: int,
    qualification: Qualification | None = None,
) -> tuple[
    RoleProfile,
    RoleProfile,
]:
    return (
        ascending_role(
            source_sex,
            generations,
            qualification,
        ),
        descending_role(
            target_sex,
            generations,
            qualification,
        ),
    )


def reciprocal_lateral(
    first_sex: SexMarker,
    second_sex: SexMarker,
    qualification: Qualification | None = None,
) -> tuple[
    RoleProfile,
    RoleProfile,
]:
    return (
        lateral_role(
            first_sex,
            qualification,
        ),
        lateral_role(
            second_sex,
            qualification,
        ),
    )


def reciprocal_aunt_nephew(
    ascending_sex: SexMarker,
    descending_sex: SexMarker,
    generations: int = 1,
    qualification: Qualification | None = None,
) -> tuple[
    RoleProfile,
    RoleProfile,
]:
    return (
        aunt_uncle_role(
            ascending_sex,
            generations,
            qualification,
        ),
        niece_nephew_role(
            descending_sex,
            generations,
            qualification,
        ),
    )


def reciprocal_cousins(
    first_sex: SexMarker,
    second_sex: SexMarker,
    degree: int,
    removal: int = 0,
) -> tuple[
    RoleProfile,
    RoleProfile,
]:
    return (
        cousin_role(
            first_sex,
            degree,
            removal,
        ),
        cousin_role(
            second_sex,
            degree,
            removal,
        ),
    )


def canonical_profile_catalog() -> tuple[
    RoleProfile,
    ...,
]:
    profiles: list[
        RoleProfile
    ] = []

    for sex in SexMarker:
        profiles.extend(
            [
                ascending_role(
                    sex,
                    1,
                ),
                descending_role(
                    sex,
                    1,
                ),
                ascending_role(
                    sex,
                    2,
                ),
                descending_role(
                    sex,
                    2,
                ),
                lateral_role(
                    sex,
                    Qualification.FULL,
                ),
                lateral_role(
                    sex,
                    Qualification.HALF,
                ),
                lateral_role(
                    sex,
                    Qualification.ADOPTIVE,
                ),
                lateral_role(
                    sex,
                    Qualification.STEP,
                ),
                aunt_uncle_role(
                    sex,
                ),
                niece_nephew_role(
                    sex,
                ),
                cousin_role(
                    sex,
                    1,
                ),
                cousin_role(
                    sex,
                    2,
                ),
                ascending_role(
                    sex,
                    1,
                    Qualification.BIOLOGICAL,
                ),
                ascending_role(
                    sex,
                    1,
                    Qualification.ADOPTIVE,
                ),
                ascending_role(
                    sex,
                    1,
                    Qualification.STEP,
                ),
                ascending_role(
                    sex,
                    1,
                    Qualification.FOSTER,
                ),
                ascending_role(
                    sex,
                    1,
                    Qualification.LEGAL,
                ),
                descending_role(
                    sex,
                    1,
                    Qualification.BIOLOGICAL,
                ),
                descending_role(
                    sex,
                    1,
                    Qualification.ADOPTIVE,
                ),
                descending_role(
                    sex,
                    1,
                    Qualification.STEP,
                ),
                descending_role(
                    sex,
                    1,
                    Qualification.FOSTER,
                ),
                descending_role(
                    sex,
                    1,
                    Qualification.LEGAL,
                ),
                guardian_role(
                    sex,
                ),
                alliance_role(
                    sex,
                ),
                affinity_ascending_role(
                    sex,
                ),
                affinity_descending_role(
                    sex,
                ),
                affinity_lateral_role(
                    sex,
                ),
            ]
        )

    return tuple(
        sorted(
            profiles,
            key=lambda profile:
                profile.role_id,
        )
    )


def enhancements() -> tuple[str, ...]:
    return (
        "specific_gendered_canonical_roles",
        "symmetric_reciprocal_roles",
        "neutral_internal_geometry",
        "direct_edge_first_semantics",
        "deterministic_role_projection",
        "stable_role_identity",
        "unbounded_ancestral_depth",
        "unbounded_descendant_depth",
        "unbounded_cousin_degree",
        "unbounded_cousin_removal",
        "female_cousin_projection",
        "male_cousin_projection",
        "full_lateral_qualification",
        "half_lateral_qualification",
        "evidence_gated_full_qualification",
        "unresolved_incomplete_full_evidence",
        "lateral_derivation_certificates",
        "shared_ascendant_provenance",
        "adoptive_role_qualification",
        "step_role_qualification",
        "foster_role_qualification",
        "legal_role_qualification",
        "gender_specific_guardianship",
        "gender_specific_affinity",
        "gender_specific_alliance",
        "temporal_alliance_compatibility",
        "inverse_role_projection",
        "multi_generation_role_projection",
        "great_generation_projection",
        "qualification_composition",
        "immutable_role_profiles",
        "immutable_derivation_profiles",
        "cached_deterministic_projection",
        "bounded_validation",
        "relationship_axis_separation",
        "descent_affinity_separation",
        "guardianship_descent_separation",
        "no_duplicate_relationship_authority",
        "no_derived_relationship_storage_requirement",
        "policy_ready_role_profiles",
        "provenance_ready_role_identity",
    )


def health() -> dict[str, object]:
    catalog = canonical_profile_catalog()

    ids = [
        profile.role_id
        for profile in catalog
    ]

    return {
        "healthy":
            len(ids)
            == len(set(ids)),
        "profile_count":
            len(ids),
        "enhancement_count":
            len(enhancements()),
        "sex_markers": [
            value.value
            for value in SexMarker
        ],
        "axes": [
            value.value
            for value in Axis
        ],
        "qualifications": [
            value.value
            for value in Qualification
        ],
        "generic_family_roles_canonical":
            False,
        "full_half_derivation":
            "evidence_gated",
    }
