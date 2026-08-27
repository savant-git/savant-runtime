#!/usr/bin/env python3

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ROOT = Path("/root/savant-runtime")

INSTANCE_ROOT = (
    ROOT
    / "runtime/scrybe/instances"
)


class ScrybeInstanceError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class ScrybeInstance:
    instance_id: str
    owner: str
    focal: str
    authority_state: str
    projection_authoritative: bool
    independent_memory_store: bool
    canonical_memory_store: str
    retrieval: Mapping[str, Any]
    behavior: Mapping[str, Any]
    enhancement_groups: Mapping[
        str,
        tuple[str, ...],
    ]

    @property
    def enhancement_count(
        self,
    ) -> int:
        return sum(
            len(values)
            for values
            in self.enhancement_groups.values()
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "instance_id":
                self.instance_id,
            "owner":
                self.owner,
            "focal":
                self.focal,
            "authority_state":
                self.authority_state,
            "projection_authoritative":
                self.projection_authoritative,
            "independent_memory_store":
                self.independent_memory_store,
            "canonical_memory_store":
                self.canonical_memory_store,
            "retrieval":
                dict(
                    self.retrieval
                ),
            "behavior":
                dict(
                    self.behavior
                ),
            "enhancement_groups": {
                key:
                    list(values)
                for key, values
                in self
                .enhancement_groups
                .items()
            },
            "enhancement_count":
                self.enhancement_count,
        }


def _require_bool(
    value: Any,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise ScrybeInstanceError(
            f"{name} must be boolean"
        )

    return value


def _require_number(
    value: Any,
    name: str,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    if not isinstance(
        value,
        (int, float),
    ):
        raise ScrybeInstanceError(
            f"{name} must be numeric"
        )

    result = float(
        value
    )

    if not (
        minimum
        <= result
        <= maximum
    ):
        raise ScrybeInstanceError(
            f"{name} outside "
            f"{minimum}..{maximum}"
        )

    return result


def load_instance(
    name: str = "lore",
) -> ScrybeInstance:
    path = (
        INSTANCE_ROOT
        / f"{name}.json"
    )

    if not path.is_file():
        raise ScrybeInstanceError(
            "missing Scrybe instance: "
            + str(path)
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if (
        payload.get("substrate")
        != "scrybe"
    ):
        raise ScrybeInstanceError(
            "invalid substrate identity"
        )

    if (
        payload.get(
            "projection_authoritative"
        )
        is not False
    ):
        raise ScrybeInstanceError(
            "Scrybe projections "
            "must remain non-authoritative"
        )

    if (
        payload.get(
            "independent_memory_store"
        )
        is not False
    ):
        raise ScrybeInstanceError(
            "Scrybe must not own "
            "an independent memory store"
        )

    if (
        payload.get(
            "canonical_memory_store"
        )
        != "fluid-canon"
    ):
        raise ScrybeInstanceError(
            "Scrybe canonical memory "
            "must remain Fluid Canon"
        )

    retrieval = dict(
        payload.get(
            "retrieval",
            {},
        )
    )

    if len(retrieval) != 9:
        raise ScrybeInstanceError(
            "retrieval overlay "
            "must contain 9 controls"
        )

    candidate_multiplier = int(
        retrieval.get(
            "candidate_multiplier",
            0,
        )
    )

    if candidate_multiplier not in (
        3,
        9,
    ):
        raise ScrybeInstanceError(
            "candidate_multiplier "
            "must be 3 or 9"
        )

    context_budget = int(
        retrieval.get(
            "context_budget",
            0,
        )
    )

    if (
        context_budget <= 0
        or context_budget % 3
        != 0
    ):
        raise ScrybeInstanceError(
            "context_budget must be "
            "a positive multiple of 3"
        )

    weight_names = (
        "semantic_weight",
        "lexical_weight",
        "confidence_weight",
        "authority_weight",
        "recency_weight",
    )

    total_weight = 0.0

    for name_ in weight_names:
        total_weight += (
            _require_number(
                retrieval.get(
                    name_
                ),
                name_,
            )
        )

    if abs(
        total_weight - 1.0
    ) > 1e-9:
        raise ScrybeInstanceError(
            "retrieval weights "
            "must sum to 1.0"
        )

    _require_number(
        retrieval.get(
            "minimum_score"
        ),
        "minimum_score",
    )

    _require_bool(
        retrieval.get(
            "deduplicate"
        ),
        "deduplicate",
    )

    behavior = dict(
        payload.get(
            "behavior",
            {},
        )
    )

    if len(behavior) != 9:
        raise ScrybeInstanceError(
            "behavior overlay "
            "must contain 9 controls"
        )

    for key, value in (
        behavior.items()
    ):
        _require_bool(
            value,
            key,
        )

    raw_groups = dict(
        payload.get(
            "enhancement_groups",
            {},
        )
    )

    if len(raw_groups) != 9:
        raise ScrybeInstanceError(
            "Scrybe requires "
            "9 enhancement groups"
        )

    groups: dict[
        str,
        tuple[str, ...],
    ] = {}

    for key, values in (
        raw_groups.items()
    ):
        if (
            not isinstance(
                values,
                list,
            )
            or len(values) != 3
            or not all(
                isinstance(
                    item,
                    str,
                )
                and item.strip()
                for item in values
            )
        ):
            raise ScrybeInstanceError(
                f"{key} must contain "
                "exactly 3 enhancements"
            )

        groups[key] = tuple(
            values
        )

    instance = ScrybeInstance(
        instance_id=str(
            payload[
                "instance_id"
            ]
        ),
        owner=str(
            payload["owner"]
        ),
        focal=str(
            payload["focal"]
        ),
        authority_state=str(
            payload[
                "authority_state"
            ]
        ),
        projection_authoritative=False,
        independent_memory_store=False,
        canonical_memory_store=(
            "fluid-canon"
        ),
        retrieval=MappingProxyType(
            retrieval
        ),
        behavior=MappingProxyType(
            behavior
        ),
        enhancement_groups=(
            MappingProxyType(
                groups
            )
        ),
    )

    if (
        instance
        .enhancement_count
        != 27
    ):
        raise ScrybeInstanceError(
            "Scrybe must expose "
            "27 enhancements"
        )

    return instance
