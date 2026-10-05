#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping

from role_calculus import (
    KindredRoleError,
    Qualification,
    RoleProfile,
    SexMarker,
    ascending_role,
    descending_role,
    guardian_role,
    lateral_role,
)


class QualifiedBondKind(str, Enum):
    ADOPTION = "adoption"
    STEP = "step"
    GUARDIANSHIP = "guardianship"
    FOSTER = "foster"
    LEGAL = "legal"


@dataclass(
    frozen=True,
    slots=True,
)
class QualifiedBond:
    bond_id: str
    source: str
    target: str
    kind: QualifiedBondKind
    source_role: RoleProfile
    target_role: RoleProfile
    authority: str
    validity: Mapping[str, Any]
    provenance: Mapping[str, Any]
    qualifiers: Mapping[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "bond_id": self.bond_id,
            "source": self.source,
            "target": self.target,
            "kind": self.kind.value,
            "source_role":
                self.source_role.role_id,
            "target_role":
                self.target_role.role_id,
            "authority": self.authority,
            "validity":
                dict(self.validity),
            "provenance":
                dict(self.provenance),
            "qualifiers":
                dict(self.qualifiers),
        }


def _stable_bond_id(
    source: str,
    target: str,
    kind: QualifiedBondKind,
    source_role: RoleProfile,
    target_role: RoleProfile,
) -> str:
    payload = json.dumps(
        {
            "source": source,
            "target": target,
            "kind": kind.value,
            "source_role":
                source_role.role_id,
            "target_role":
                target_role.role_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    digest = sha256(
        payload
    ).hexdigest()[:24]

    return (
        f"kindred.bond."
        f"{kind.value}."
        f"{digest}"
    )


def _bond(
    *,
    source: str,
    target: str,
    kind: QualifiedBondKind,
    source_role: RoleProfile,
    target_role: RoleProfile,
    authority: str,
    validity: Mapping[
        str,
        Any,
    ] | None,
    provenance: Mapping[
        str,
        Any,
    ] | None,
    qualifiers: Mapping[
        str,
        Any,
    ] | None,
) -> QualifiedBond:
    source = source.strip()
    target = target.strip()

    if not source:
        raise KindredRoleError(
            "source is required"
        )

    if not target:
        raise KindredRoleError(
            "target is required"
        )

    if source == target:
        raise KindredRoleError(
            "kindred bond endpoints "
            "must be distinct"
        )

    return QualifiedBond(
        bond_id=_stable_bond_id(
            source,
            target,
            kind,
            source_role,
            target_role,
        ),
        source=source,
        target=target,
        kind=kind,
        source_role=source_role,
        target_role=target_role,
        authority=authority,
        validity=dict(
            validity or {}
        ),
        provenance=dict(
            provenance or {}
        ),
        qualifiers=dict(
            qualifiers or {}
        ),
    )


def adoption(
    *,
    ascending_instance: str,
    descending_instance: str,
    ascending_sex: SexMarker,
    descending_sex: SexMarker,
    authority: str = "FOUNDATION-008",
    validity: Mapping[
        str,
        Any,
    ] | None = None,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    qualifiers: Mapping[
        str,
        Any,
    ] | None = None,
) -> QualifiedBond:
    return _bond(
        source=ascending_instance,
        target=descending_instance,
        kind=QualifiedBondKind.ADOPTION,
        source_role=ascending_role(
            ascending_sex,
            1,
            Qualification.ADOPTIVE,
        ),
        target_role=descending_role(
            descending_sex,
            1,
            Qualification.ADOPTIVE,
        ),
        authority=authority,
        validity=validity,
        provenance=provenance,
        qualifiers=qualifiers,
    )


def step_relation(
    *,
    ascending_instance: str,
    descending_instance: str,
    ascending_sex: SexMarker,
    descending_sex: SexMarker,
    authority: str = "FOUNDATION-008",
    validity: Mapping[
        str,
        Any,
    ] | None = None,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    qualifiers: Mapping[
        str,
        Any,
    ] | None = None,
) -> QualifiedBond:
    return _bond(
        source=ascending_instance,
        target=descending_instance,
        kind=QualifiedBondKind.STEP,
        source_role=ascending_role(
            ascending_sex,
            1,
            Qualification.STEP,
        ),
        target_role=descending_role(
            descending_sex,
            1,
            Qualification.STEP,
        ),
        authority=authority,
        validity=validity,
        provenance=provenance,
        qualifiers=qualifiers,
    )


def guardianship(
    *,
    guardian_instance: str,
    ward_instance: str,
    guardian_sex: SexMarker,
    ward_sex: SexMarker,
    authority: str = "FOUNDATION-008",
    validity: Mapping[
        str,
        Any,
    ] | None = None,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    qualifiers: Mapping[
        str,
        Any,
    ] | None = None,
) -> QualifiedBond:
    ward_label = (
        "female_ward"
        if ward_sex is SexMarker.FEMALE
        else "male_ward"
    )

    ward_role = RoleProfile(
        role_id=(
            f"kindred.role."
            f"{ward_label}"
        ),
        label=ward_label,
        sex=ward_sex,
        axis=guardian_role(
            guardian_sex
        ).axis,
        qualification=
            Qualification.GUARDIAN,
    )

    return _bond(
        source=guardian_instance,
        target=ward_instance,
        kind=
            QualifiedBondKind.GUARDIANSHIP,
        source_role=guardian_role(
            guardian_sex
        ),
        target_role=ward_role,
        authority=authority,
        validity=validity,
        provenance=provenance,
        qualifiers=qualifiers,
    )


def foster_relation(
    *,
    ascending_instance: str,
    descending_instance: str,
    ascending_sex: SexMarker,
    descending_sex: SexMarker,
    authority: str = "FOUNDATION-008",
    validity: Mapping[
        str,
        Any,
    ] | None = None,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    qualifiers: Mapping[
        str,
        Any,
    ] | None = None,
) -> QualifiedBond:
    return _bond(
        source=ascending_instance,
        target=descending_instance,
        kind=QualifiedBondKind.FOSTER,
        source_role=ascending_role(
            ascending_sex,
            1,
            Qualification.FOSTER,
        ),
        target_role=descending_role(
            descending_sex,
            1,
            Qualification.FOSTER,
        ),
        authority=authority,
        validity=validity,
        provenance=provenance,
        qualifiers=qualifiers,
    )


def legal_relation(
    *,
    ascending_instance: str,
    descending_instance: str,
    ascending_sex: SexMarker,
    descending_sex: SexMarker,
    authority: str = "FOUNDATION-008",
    validity: Mapping[
        str,
        Any,
    ] | None = None,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
    qualifiers: Mapping[
        str,
        Any,
    ] | None = None,
) -> QualifiedBond:
    return _bond(
        source=ascending_instance,
        target=descending_instance,
        kind=QualifiedBondKind.LEGAL,
        source_role=ascending_role(
            ascending_sex,
            1,
            Qualification.LEGAL,
        ),
        target_role=descending_role(
            descending_sex,
            1,
            Qualification.LEGAL,
        ),
        authority=authority,
        validity=validity,
        provenance=provenance,
        qualifiers=qualifiers,
    )


def lateral_adoption(
    *,
    first_instance: str,
    second_instance: str,
    first_sex: SexMarker,
    second_sex: SexMarker,
    authority: str = "FOUNDATION-008",
    validity: Mapping[
        str,
        Any,
    ] | None = None,
    provenance: Mapping[
        str,
        Any,
    ] | None = None,
) -> tuple[
    QualifiedBond,
    QualifiedBond,
]:
    first_role = lateral_role(
        first_sex,
        Qualification.ADOPTIVE,
    )

    second_role = lateral_role(
        second_sex,
        Qualification.ADOPTIVE,
    )

    return (
        _bond(
            source=first_instance,
            target=second_instance,
            kind=QualifiedBondKind.ADOPTION,
            source_role=first_role,
            target_role=second_role,
            authority=authority,
            validity=validity,
            provenance=provenance,
            qualifiers={
                "projection": "lateral",
            },
        ),
        _bond(
            source=second_instance,
            target=first_instance,
            kind=QualifiedBondKind.ADOPTION,
            source_role=second_role,
            target_role=first_role,
            authority=authority,
            validity=validity,
            provenance=provenance,
            qualifiers={
                "projection": "lateral",
            },
        ),
    )
