#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping


class AllianceAffinityError(ValueError):
    pass


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _stable_id(
    *,
    source: str,
    target: str,
    role: str,
    axis: str,
    scope: str,
) -> str:
    digest = sha256(
        _canonical_json(
            {
                "source": source,
                "target": target,
                "role": role,
                "axis": axis,
                "scope": scope,
            }
        ).encode("utf-8")
    ).hexdigest()[:24]

    return (
        f"kindred.{axis}.{role}.{digest}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AllianceAffinityBinding:
    id: str
    source: str
    target: str
    role: str
    axis: str
    scope: str = "kindred"
    status: str = "active"
    authority: str = "FOUNDATION-008"
    version: str = "1.0.0"
    validity: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )
    provenance: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )
    qualifiers: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )
    extensions: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "AllianceAffinityBinding":
        source = str(
            value.get(
                "source",
                "",
            )
        ).strip()

        target = str(
            value.get(
                "target",
                "",
            )
        ).strip()

        role = str(
            value.get(
                "role",
                "",
            )
        ).strip().lower()

        axis = str(
            value.get(
                "axis",
                "",
            )
        ).strip().lower()

        scope = str(
            value.get(
                "scope",
                "kindred",
            )
        ).strip() or "kindred"

        if not source:
            raise AllianceAffinityError(
                "source is required"
            )

        if not target:
            raise AllianceAffinityError(
                "target is required"
            )

        if source == target:
            raise AllianceAffinityError(
                "alliance or affinity endpoints "
                "must be distinct"
            )

        if not role:
            raise AllianceAffinityError(
                "role is required"
            )

        if axis not in {
            "alliance",
            "affinity",
        }:
            raise AllianceAffinityError(
                "axis must be alliance or affinity"
            )

        binding_id = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if not binding_id:
            binding_id = _stable_id(
                source=source,
                target=target,
                role=role,
                axis=axis,
                scope=scope,
            )

        return cls(
            id=binding_id,
            source=source,
            target=target,
            role=role,
            axis=axis,
            scope=scope,
            status=str(
                value.get(
                    "status",
                    "active",
                )
            ).strip() or "active",
            authority=str(
                value.get(
                    "authority",
                    "FOUNDATION-008",
                )
            ).strip() or "FOUNDATION-008",
            version=str(
                value.get(
                    "version",
                    "1.0.0",
                )
            ).strip() or "1.0.0",
            validity=deepcopy(
                dict(
                    value.get(
                        "validity"
                    )
                    or {}
                )
            ),
            provenance=deepcopy(
                dict(
                    value.get(
                        "provenance"
                    )
                    or {}
                )
            ),
            qualifiers=deepcopy(
                dict(
                    value.get(
                        "qualifiers"
                    )
                    or {}
                )
            ),
            extensions=deepcopy(
                dict(
                    value.get(
                        "extensions"
                    )
                    or {}
                )
            ),
        )

    def to_segue(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "segue",
            "type": "lineage",
            "status": self.status,
            "authority": self.authority,
            "version": self.version,
            "parent": self.source,
            "child": self.target,
            "role": self.role,
            "axis": self.axis,
            "continuation": "neutral",
            "scope": self.scope,
            "order": 0,
            "inheritance": {
                "mode": "none",
                "fields": [],
                "exclude": [],
                "conflict_policy":
                    "child_wins",
            },
            "propagation": {
                "enabled": False,
                "channels": [],
            },
            "validity": deepcopy(
                dict(self.validity)
            ),
            "provenance": deepcopy(
                dict(self.provenance)
            ),
            "metadata": {
                "kindred": {
                    "axis": self.axis,
                    "qualifiers": deepcopy(
                        dict(
                            self.qualifiers
                        )
                    ),
                }
            },
            "extensions": deepcopy(
                dict(self.extensions)
            ),
            "future_extensions": {},
        }


def alliance(
    source: str,
    target: str,
    *,
    role: str = "alliance",
    scope: str = "kindred",
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
    extensions: Mapping[
        str,
        Any,
    ] | None = None,
) -> AllianceAffinityBinding:
    return AllianceAffinityBinding.from_mapping(
        {
            "source": source,
            "target": target,
            "role": role,
            "axis": "alliance",
            "scope": scope,
            "validity": validity or {},
            "provenance": provenance or {},
            "qualifiers": qualifiers or {},
            "extensions": extensions or {},
        }
    )


def affinity(
    source: str,
    target: str,
    *,
    role: str = "affinity",
    scope: str = "kindred",
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
    extensions: Mapping[
        str,
        Any,
    ] | None = None,
) -> AllianceAffinityBinding:
    return AllianceAffinityBinding.from_mapping(
        {
            "source": source,
            "target": target,
            "role": role,
            "axis": "affinity",
            "scope": scope,
            "validity": validity or {},
            "provenance": provenance or {},
            "qualifiers": qualifiers or {},
            "extensions": extensions or {},
        }
    )
