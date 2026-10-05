from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/conscience/1"

APPRAISAL_CLASSES = frozenset(
    {
        "aligned",
        "conflicted",
        "violated",
        "uncertain",
    }
)


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class ConscienceAppraisal:
    action_ref: str
    value_ref: str
    appraisal_class: str
    alignment: float
    responsibility: float
    consequence: float
    uncertainty: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.action_ref:
            raise ValueError(
                "action_ref is required"
            )

        if not self.value_ref:
            raise ValueError(
                "value_ref is required"
            )

        if (
            self.appraisal_class
            not in APPRAISAL_CLASSES
        ):
            raise ValueError(
                "unsupported appraisal class"
            )

        if not (
            -1.0
            <= float(self.alignment)
            <= 1.0
        ):
            raise ValueError(
                "alignment must be between "
                "-1 and 1"
            )

        for value in (
            self.responsibility,
            self.consequence,
            self.uncertainty,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "conscience values must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "action_ref": self.action_ref,
            "value_ref": self.value_ref,
            "appraisal_class": (
                self.appraisal_class
            ),
            "alignment": float(
                self.alignment
            ),
            "responsibility": float(
                self.responsibility
            ),
            "consequence": float(
                self.consequence
            ),
            "uncertainty": float(
                self.uncertainty
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-conscience:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class MoralResidue:
    appraisal_ref: str
    pressure: float
    repair_pressure: float
    uncertainty: float
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.appraisal_ref:
            raise ValueError(
                "appraisal_ref is required"
            )

        for value in (
            self.pressure,
            self.repair_pressure,
            self.uncertainty,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "moral residue values must "
                    "be between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "appraisal_ref": (
                self.appraisal_ref
            ),
            "pressure": float(
                self.pressure
            ),
            "repair_pressure": float(
                self.repair_pressure
            ),
            "uncertainty": float(
                self.uncertainty
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


@dataclass(frozen=True, slots=True)
class Repair:
    appraisal_ref: str
    repair_ref: str
    acknowledgment: float
    restitution: float
    changed_behavior: float
    acceptance: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.appraisal_ref:
            raise ValueError(
                "appraisal_ref is required"
            )

        if not self.repair_ref:
            raise ValueError(
                "repair_ref is required"
            )

        for value in (
            self.acknowledgment,
            self.restitution,
            self.changed_behavior,
            self.acceptance,
        ):
            if not (
                0.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "repair values must be "
                    "between 0 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "appraisal_ref": (
                self.appraisal_ref
            ),
            "repair_ref": self.repair_ref,
            "acknowledgment": float(
                self.acknowledgment
            ),
            "restitution": float(
                self.restitution
            ),
            "changed_behavior": float(
                self.changed_behavior
            ),
            "acceptance": float(
                self.acceptance
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_effect": "none",
        }


def derive_moral_residue(
    appraisal: ConscienceAppraisal,
) -> MoralResidue:
    violation = _unit(
        max(
            0.0,
            -float(
                appraisal.alignment
            ),
        )
    )

    attributable = (
        violation
        * float(
            appraisal.responsibility
        )
    )

    consequential = (
        attributable
        * (
            0.5
            + (
                0.5
                * float(
                    appraisal.consequence
                )
            )
        )
    )

    pressure = _unit(
        consequential
    )

    repair_pressure = _unit(
        pressure
        * (
            1.0
            - (
                0.5
                * float(
                    appraisal.uncertainty
                )
            )
        )
    )

    return MoralResidue(
        appraisal_ref=appraisal.id,
        pressure=pressure,
        repair_pressure=(
            repair_pressure
        ),
        uncertainty=(
            appraisal.uncertainty
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *appraisal.causal_refs,
                    appraisal.id,
                )
            )
        ),
    )


def apply_repair(
    residue: MoralResidue,
    repair: Repair,
) -> MoralResidue:
    if (
        repair.appraisal_ref
        != residue.appraisal_ref
    ):
        raise ValueError(
            "repair appraisal mismatch"
        )

    effectiveness = (
        float(repair.acknowledgment)
        + float(repair.restitution)
        + float(
            repair.changed_behavior
        )
        + float(repair.acceptance)
    ) / 4.0

    remaining = _unit(
        float(residue.pressure)
        * (
            1.0
            - effectiveness
        )
    )

    return MoralResidue(
        appraisal_ref=(
            residue.appraisal_ref
        ),
        pressure=remaining,
        repair_pressure=remaining,
        uncertainty=(
            residue.uncertainty
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *residue.causal_refs,
                    repair.repair_ref,
                    *repair.causal_refs,
                )
            )
        ),
    )


def conscience_projection(
    appraisal: ConscienceAppraisal,
    residue: MoralResidue,
    *,
    repairs: Sequence[Repair] = (),
) -> Mapping[str, Any]:
    if (
        residue.appraisal_ref
        != appraisal.id
    ):
        raise ValueError(
            "residue appraisal mismatch"
        )

    return {
        "schema": SCHEMA,
        "appraisal": (
            appraisal.projection()
        ),
        "moral_residue": (
            residue.projection()
        ),
        "repair_refs": [
            repair.repair_ref
            for repair in repairs
        ],
        "repair_erased_history": False,
        "external_authority_upgraded": False,
        "derived": True,
        "authoritative": False,
    }
