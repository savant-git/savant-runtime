#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, MutableMapping, Sequence


class LineageError(Exception):
    """Base functional-lineage error."""


class LineageValidationError(LineageError):
    """Raised when authoritative lineage is invalid."""


VALID_INHERITANCE_MODES = {
    "none",
    "reference",
    "merge",
    "replace",
}

VALID_CONFLICT_POLICIES = {
    "child_wins",
    "parent_wins",
    "collect",
    "error",
}

VALID_CONTINUATIONS = {
    "neutral",
    "preserving",
    "projecting",
    "transforming",
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def stable_hash(value: Any) -> str:
    return sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def stable_binding_id(
    parent: str,
    child: str,
    role: str,
    scope: str = "global",
    order: int = 0,
) -> str:
    digest = stable_hash(
        {
            "parent": parent,
            "child": child,
            "role": role,
            "scope": scope,
            "order": order,
        }
    )[:20]

    return f"lineage.{role}.{digest}"


def _string_list(
    value: Any,
    field_name: str,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise LineageValidationError(
            f"{field_name} must be an array of strings"
        )

    result: list[str] = []

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LineageValidationError(
                f"{field_name} contains an invalid value"
            )

        if item not in result:
            result.append(item)

    return tuple(result)


@dataclass(frozen=True, slots=True)
class InheritancePolicy:
    mode: str = "reference"
    fields: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    conflict_policy: str = "child_wins"

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any] | None,
        *,
        defaults: Mapping[str, Any] | None = None,
    ) -> "InheritancePolicy":
        merged: dict[str, Any] = dict(defaults or {})

        for key, item in dict(value or {}).items():
            if item not in (None, "default"):
                merged[key] = item

        mode = str(
            merged.get(
                "mode",
                "reference",
            )
        )

        conflict_policy = str(
            merged.get(
                "conflict_policy",
                "child_wins",
            )
        )

        if mode not in VALID_INHERITANCE_MODES:
            raise LineageValidationError(
                f"unsupported inheritance mode: {mode}"
            )

        if conflict_policy not in VALID_CONFLICT_POLICIES:
            raise LineageValidationError(
                "unsupported inheritance conflict policy: "
                f"{conflict_policy}"
            )

        return cls(
            mode=mode,
            fields=_string_list(
                merged.get("fields", ()),
                "inheritance.fields",
            ),
            exclude=_string_list(
                merged.get("exclude", ()),
                "inheritance.exclude",
            ),
            conflict_policy=conflict_policy,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "fields": list(self.fields),
            "exclude": list(self.exclude),
            "conflict_policy": self.conflict_policy,
        }


@dataclass(frozen=True, slots=True)
class PropagationPolicy:
    enabled: bool = True
    channels: tuple[str, ...] = (
        "validation",
        "projection",
        "regeneration",
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any] | None,
        *,
        default_enabled: bool = True,
    ) -> "PropagationPolicy":
        raw = dict(value or {})

        enabled = raw.get(
            "enabled",
            default_enabled,
        )

        if not isinstance(enabled, bool):
            raise LineageValidationError(
                "propagation.enabled must be boolean"
            )

        channels = _string_list(
            raw.get(
                "channels",
                (
                    "validation",
                    "projection",
                    "regeneration",
                ),
            ),
            "propagation.channels",
        )

        return cls(
            enabled=enabled,
            channels=channels,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "channels": list(self.channels),
        }


@dataclass(frozen=True, slots=True)
class LineageBinding:
    id: str
    parent: str
    child: str
    role: str
    axis: str

    continuation: str = "neutral"
    scope: str = "global"
    order: int = 0
    status: str = "active"
    authority: Any = "FOUNDATION-008"
    version: str = "1.0.0"

    inheritance: InheritancePolicy = field(
        default_factory=InheritancePolicy
    )

    propagation: PropagationPolicy = field(
        default_factory=PropagationPolicy
    )

    validity: Mapping[str, Any] = field(
        default_factory=dict
    )

    provenance: Mapping[str, Any] = field(
        default_factory=dict
    )

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    extensions: Mapping[str, Any] = field(
        default_factory=dict
    )

    future_extensions: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        canonical_role: str,
        axis: str,
        default_inheritance: Mapping[str, Any],
        default_propagation: bool,
    ) -> "LineageBinding":
        parent = str(
            value.get(
                "parent",
                "",
            )
        ).strip()

        child = str(
            value.get(
                "child",
                "",
            )
        ).strip()

        if not parent or not child:
            raise LineageValidationError(
                "lineage segue requires parent and child"
            )

        if parent == child:
            raise LineageValidationError(
                f"self-parenting is invalid: {parent}"
            )

        continuation = str(
            value.get(
                "continuation",
                "neutral",
            )
        )

        if continuation not in VALID_CONTINUATIONS:
            raise LineageValidationError(
                "unsupported continuation mode: "
                f"{continuation}"
            )

        scope = str(
            value.get(
                "scope",
                "global",
            )
        ).strip() or "global"

        order_raw = value.get(
            "order",
            0,
        )

        if isinstance(order_raw, bool) or not isinstance(
            order_raw,
            int,
        ):
            raise LineageValidationError(
                "lineage order must be an integer"
            )

        binding_id = str(
            value.get(
                "id",
                "",
            )
        ).strip() or stable_binding_id(
            parent,
            child,
            canonical_role,
            scope,
            order_raw,
        )

        return cls(
            id=binding_id,
            parent=parent,
            child=child,
            role=canonical_role,
            axis=axis,
            continuation=continuation,
            scope=scope,
            order=order_raw,
            status=str(
                value.get(
                    "status",
                    "active",
                )
            ),
            authority=deepcopy(
                value.get(
                    "authority",
                    "FOUNDATION-008",
                )
            ),
            version=str(
                value.get(
                    "version",
                    "1.0.0",
                )
            ),
            inheritance=InheritancePolicy.from_mapping(
                value.get("inheritance"),
                defaults=default_inheritance,
            ),
            propagation=PropagationPolicy.from_mapping(
                value.get("propagation"),
                default_enabled=default_propagation,
            ),
            validity=deepcopy(
                dict(
                    value.get("validity")
                    or {}
                )
            ),
            provenance=deepcopy(
                dict(
                    value.get("provenance")
                    or {}
                )
            ),
            metadata=deepcopy(
                dict(
                    value.get("metadata")
                    or {}
                )
            ),
            extensions=deepcopy(
                dict(
                    value.get("extensions")
                    or {}
                )
            ),
            future_extensions=deepcopy(
                dict(
                    value.get("future_extensions")
                    or {}
                )
            ),
        )

    def signature(
        self,
    ) -> tuple[str, str, str, str, int]:
        return (
            self.parent,
            self.child,
            self.role,
            self.scope,
            self.order,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "segue",
            "type": "lineage",
            "status": self.status,
            "authority": deepcopy(
                self.authority
            ),
            "version": self.version,
            "parent": self.parent,
            "child": self.child,
            "role": self.role,
            "axis": self.axis,
            "continuation": self.continuation,
            "scope": self.scope,
            "order": self.order,
            "inheritance": self.inheritance.to_dict(),
            "propagation": self.propagation.to_dict(),
            "validity": deepcopy(
                dict(self.validity)
            ),
            "provenance": deepcopy(
                dict(self.provenance)
            ),
            "metadata": deepcopy(
                dict(self.metadata)
            ),
            "extensions": deepcopy(
                dict(self.extensions)
            ),
            "future_extensions": deepcopy(
                dict(self.future_extensions)
            ),
        }


def select_top_level_fields(
    payload: Mapping[str, Any],
    fields: Sequence[str],
    exclude: Sequence[str],
) -> dict[str, Any]:
    excluded = set(exclude)

    if not fields:
        return {
            key: deepcopy(value)
            for key, value in payload.items()
            if key not in excluded
        }

    return {
        key: deepcopy(payload[key])
        for key in fields
        if key in payload
        and key not in excluded
    }


def merge_values(
    left: Any,
    right: Any,
    *,
    conflict_policy: str,
    path: str = "$",
) -> Any:
    if isinstance(left, Mapping) and isinstance(
        right,
        Mapping,
    ):
        result: MutableMapping[str, Any] = deepcopy(
            dict(left)
        )

        for key in sorted(right):
            next_path = f"{path}.{key}"

            if key not in result:
                result[key] = deepcopy(
                    right[key]
                )
            else:
                result[key] = merge_values(
                    result[key],
                    right[key],
                    conflict_policy=conflict_policy,
                    path=next_path,
                )

        return dict(result)

    if left == right:
        return deepcopy(left)

    if conflict_policy == "child_wins":
        return deepcopy(right)

    if conflict_policy == "parent_wins":
        return deepcopy(left)

    if conflict_policy == "collect":
        values: list[Any] = []

        for item in (
            left,
            right,
        ):
            candidates = (
                item
                if isinstance(item, list)
                else [item]
            )

            for candidate in candidates:
                if candidate not in values:
                    values.append(
                        deepcopy(candidate)
                    )

        return values

    if conflict_policy == "error":
        raise LineageValidationError(
            f"inheritance conflict at {path}"
        )

    raise LineageValidationError(
        "unsupported conflict policy: "
        f"{conflict_policy}"
    )
