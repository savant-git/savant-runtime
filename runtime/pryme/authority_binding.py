#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .engine import (
    AuthorityRecord,
    Pryme,
)


OWNER = "living:pryme"
SCHEMA = "savant://runtime/pryme/authority-binding/1.1.0"


class PrymeAuthorityBindingError(RuntimeError):
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


def normalized_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return text or None


def normalized_string_set(
    value: Any,
) -> frozenset[str]:
    if value is None:
        return frozenset()

    if isinstance(
        value,
        str,
    ):
        item = normalized_identifier(
            value
        )

        return (
            frozenset(
                (item,)
            )
            if item
            else frozenset()
        )

    if isinstance(
        value,
        Mapping,
    ):
        values = value.keys()
    else:
        try:
            values = iter(
                value
            )
        except TypeError:
            values = (
                value,
            )

    result: set[str] = set()

    for item in values:
        normalized = normalized_identifier(
            item
        )

        if normalized:
            result.add(
                normalized
            )

    return frozenset(
        result
    )


def primitive_mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return dict(
            value
        )

    to_primitives = getattr(
        value,
        "to_primitives",
        None,
    )

    if callable(
        to_primitives
    ):
        result = to_primitives()

        if isinstance(
            result,
            Mapping,
        ):
            return dict(
                result
            )

    result: dict[str, Any] = {}

    for name in (
        "id",
        "kind",
        "status",
        "authority",
        "lineage",
        "provenance",
        "relationships",
        "dependencies",
        "metadata",
        "version",
        "canonical_name",
        "display_name",
        "description",
    ):
        if hasattr(
            value,
            name,
        ):
            result[
                name
            ] = getattr(
                value,
                name
            )

    return result


def registry_values(
    registry: Any,
) -> tuple[Any, ...]:
    values = getattr(
        registry,
        "values",
        None,
    )

    if callable(
        values
    ):
        result = values()

        return tuple(
            result
        )

    if isinstance(
        registry,
        Mapping,
    ):
        return tuple(
            registry.values()
        )

    if isinstance(
        registry,
        Iterable,
    ) and not isinstance(
        registry,
        (
            str,
            bytes,
        ),
    ):
        return tuple(
            registry
        )

    raise PrymeAuthorityBindingError(
        "unsupported constitutional registry"
    )


def authority_class_from(
    payload: Mapping[str, Any],
) -> str | None:
    authority = payload.get(
        "authority"
    )

    if isinstance(
        authority,
        str,
    ):
        return (
            normalized_identifier(
                authority
            )
        )

    if isinstance(
        authority,
        Mapping,
    ):
        for key in (
            "class",
            "authority_class",
            "tier",
            "source_class",
            "precedence_class",
        ):
            candidate = (
                normalized_identifier(
                    authority.get(
                        key
                    )
                )
            )

            if candidate:
                return candidate

    metadata = payload.get(
        "metadata"
    )

    if isinstance(
        metadata,
        Mapping,
    ):
        for key in (
            "authority_class",
            "precedence_class",
        ):
            candidate = (
                normalized_identifier(
                    metadata.get(
                        key
                    )
                )
            )

            if candidate:
                return candidate

    return "constitutional-canon"


def supersedes_from(
    payload: Mapping[str, Any],
) -> frozenset[str]:
    lineage = payload.get(
        "lineage"
    )

    if isinstance(
        lineage,
        Mapping,
    ):
        return normalized_string_set(
            lineage.get(
                "supersedes"
            )
        )

    return normalized_string_set(
        payload.get(
            "supersedes"
        )
    )


def source_from(
    payload: Mapping[str, Any],
) -> str:
    provenance = payload.get(
        "provenance"
    )

    if isinstance(
        provenance,
        Mapping,
    ):
        sources = provenance.get(
            "sources"
        )

        if isinstance(
            sources,
            str,
        ):
            normalized = (
                normalized_identifier(
                    sources
                )
            )

            if normalized:
                return normalized

        if isinstance(
            sources,
            (
                list,
                tuple,
                set,
                frozenset,
            ),
        ):
            normalized_sources = [
                normalized_identifier(
                    item
                )
                for item in sources
            ]

            normalized_sources = [
                item
                for item
                in normalized_sources
                if item
            ]

            if normalized_sources:
                return sorted(
                    normalized_sources
                )[0]

    return "constitutional-registry"


def record_from_object(
    value: Any,
) -> AuthorityRecord:
    payload = primitive_mapping(
        value
    )

    identity = normalized_identifier(
        payload.get(
            "id"
        )
    )

    if not identity:
        raise PrymeAuthorityBindingError(
            "constitutional object "
            "has no stable identity"
        )

    kind = (
        normalized_identifier(
            payload.get(
                "kind"
            )
        )
        or "concept"
    )

    status = (
        normalized_identifier(
            payload.get(
                "status"
            )
        )
        or "unknown"
    )

    authority_class = (
        authority_class_from(
            payload
        )
    )

    source = source_from(
        payload
    )

    supersedes = (
        supersedes_from(
            payload
        )
    )

    lineage = payload.get(
        "lineage",
        {},
    )

    provenance = payload.get(
        "provenance",
        {},
    )

    fingerprint_payload = {
        "identity": identity,
        "source": source,
        "kind": kind,
        "status": status,
        "authority_class": (
            authority_class
        ),
        "supersedes": sorted(
            supersedes
        ),
        "lineage": lineage,
        "provenance": provenance,
        "payload": payload,
    }

    return AuthorityRecord(
        identity=identity,
        source=source,
        kind=kind,
        status=status,
        authority_class=(
            authority_class
        ),
        supersedes=supersedes,
        lineage=lineage,
        provenance=provenance,
        payload=payload,
        fingerprint=digest(
            fingerprint_payload
        ),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PrymeAuthorityBinding:
    pryme: Pryme
    registry: Any

    @classmethod
    def create(
        cls,
        registry: Any,
        pryme: Pryme | None = None,
    ) -> "PrymeAuthorityBinding":
        return cls(
            pryme=(
                pryme
                if pryme is not None
                else Pryme()
            ),
            registry=registry,
        )

    def records(
        self,
    ) -> tuple[
        AuthorityRecord,
        ...
    ]:
        result = tuple(
            record_from_object(
                item
            )
            for item
            in registry_values(
                self.registry
            )
        )

        identities = [
            record.identity
            for record
            in result
        ]

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise PrymeAuthorityBindingError(
                "constitutional authority "
                "binding contains duplicate "
                "identities"
            )

        return tuple(
            sorted(
                result,
                key=lambda item: (
                    item.identity,
                    item.fingerprint,
                ),
            )
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        records = self.records()

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "pryme_substrate": (
                self.pryme.substrate_id
            ),
            "record_count": len(
                records
            ),
            "records": [
                record.projection()
                for record
                in records
            ],
            "authority_manufactured": (
                False
            ),
            "authority_mutated": (
                False
            ),
            "source_authority_preserved": (
                True
            ),
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def status(
        self,
    ) -> dict[str, Any]:
        records = self.records()

        payload = {
            "schema": (
                "savant://runtime/pryme/"
                "authority-binding-status/1.1.0"
            ),
            "owner": OWNER,
            "record_count": len(
                records
            ),
            "registry_type": (
                type(
                    self.registry
                ).__name__
            ),
            "pryme_type": (
                type(
                    self.pryme
                ).__name__
            ),
            "authority_manufactured": (
                False
            ),
            "authority_mutated": (
                False
            ),
            "valid": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def bind(
    registry: Any,
    pryme: Pryme | None = None,
) -> PrymeAuthorityBinding:
    return PrymeAuthorityBinding.create(
        registry=registry,
        pryme=pryme,
    )


def bind_registry(
    registry: Any,
    pryme: Pryme | None = None,
) -> PrymeAuthorityBinding:
    return bind(
        registry,
        pryme,
    )


ConstitutionalBinding = (
    PrymeAuthorityBinding
)


__all__ = (
    "ConstitutionalBinding",
    "PrymeAuthorityBinding",
    "PrymeAuthorityBindingError",
    "bind",
    "bind_registry",
    "record_from_object",
    "registry_values",
)
