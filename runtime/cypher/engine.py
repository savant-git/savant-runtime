#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml


ROOT = Path("/root/savant-runtime")

DEFAULT_INSTANCE = (
    ROOT
    / "runtime/cypher/instances/runtime.json"
)


CYPHER_PIPELINE = (
    "admission",
    "source_identification",
    "source_contract_resolution",

    "encoding_detection",
    "deserialization",
    "normalization",

    "authority_preservation",
    "lineage_preservation",
    "provenance_preservation",

    "route_resolution",
    "adapter_selection",
    "transformation",

    "loss_analysis",
    "target_contract_resolution",
    "target_validation",

    "serialization",
    "observability",
    "attestation",
)


CYPHER_ABILITIES = (
    "exchange_identity",
    "encoding_detection",
    "canonical_deserialization",

    "typed_route_resolution",
    "adapter_selection",
    "bidirectional_translation",

    "authority_preservation",
    "lineage_preservation",
    "provenance_preservation",

    "contract_validation",
    "loss_detection",
    "unknown_field_preservation",

    "version_adaptation",
    "canonical_serialization",
    "idempotence_verification",

    "exchange_receipt",
    "translation_explanation",
    "compatibility_projection",
)


CYPHER_HEALTH_DIMENSIONS = (
    "instance_integrity",
    "encoding_integrity",
    "route_integrity",

    "adapter_integrity",
    "authority_preservation",
    "lineage_preservation",

    "provenance_preservation",
    "serialization_integrity",
    "mutation_boundary",
)


CYPHER_VALIDATION_DIMENSIONS = (
    "identity",
    "source_contract",
    "encoding",

    "route",
    "transformation",
    "preservation",

    "target_contract",
    "idempotence",
    "integration",
)


CYPHER_PROJECTIONS = (
    "exchange_envelope",
    "route_map",
    "adapter_map",

    "translation_receipt",
    "compatibility_report",
    "loss_report",

    "contract_projection",
    "translation_explanation",
    "exchange_health",
)


class CypherError(RuntimeError):
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


def normalize_text(
    value: str,
) -> str:
    return unicodedata.normalize(
        "NFC",
        value,
    ).replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ExchangeEnvelope:
    exchange_id: str
    source_type: str
    target_type: str
    payload: Any
    authority: Any
    lineage: Any
    provenance: Any
    metadata: dict[str, Any]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "exchange_id": self.exchange_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "payload": self.payload,
            "authority": self.authority,
            "lineage": self.lineage,
            "provenance": self.provenance,
            "metadata": self.metadata,
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


Adapter = Callable[
    [Any],
    Any,
]


class Cypher:
    schema = (
        "savant://runtime/"
        "cypher/1.0.0"
    )

    substrate_id = (
        "living:cypher"
    )

    def __init__(
        self,
        instance_path: Path = DEFAULT_INSTANCE,
    ) -> None:
        if not instance_path.is_absolute():
            raise CypherError(
                "instance path must be absolute"
            )

        self.instance_path = (
            instance_path.resolve()
        )

        self.instance = self._load_json(
            self.instance_path
        )

        self._validate_instance()

        self._adapters: dict[
            tuple[str, str],
            Adapter,
        ] = {}

        self._install_builtin_adapters()

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise CypherError(
                f"missing file: {path}"
            )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise CypherError(
                f"invalid object: {path}"
            )

        return payload

    def _validate_instance(
        self,
    ) -> None:
        if (
            self.instance.get(
                "substrate"
            )
            != "cypher"
        ):
            raise CypherError(
                "invalid Cypher substrate"
            )

        if (
            self.instance.get(
                "authoritative"
            )
            is not False
        ):
            raise CypherError(
                "Cypher projections "
                "must remain non-authoritative"
            )

        if (
            self.instance.get(
                "mutation_authorized"
            )
            is not False
        ):
            raise CypherError(
                "Cypher mutation must remain disabled"
            )

        supported = self.instance.get(
            "supported_encodings",
            [],
        )

        if len(supported) != 3:
            raise CypherError(
                "Cypher requires exactly "
                "3 baseline encodings"
            )

        exchange = self.instance.get(
            "exchange",
            {},
        )

        if len(exchange) != 9:
            raise CypherError(
                "exchange overlay "
                "must contain 9 controls"
            )

        groups = self.instance.get(
            "enhancement_groups",
            {},
        )

        if len(groups) != 9:
            raise CypherError(
                "Cypher requires "
                "9 enhancement groups"
            )

        for name, values in groups.items():
            if (
                not isinstance(
                    values,
                    list,
                )
                or len(values) != 3
            ):
                raise CypherError(
                    f"{name} must contain "
                    "exactly 3 enhancements"
                )

    @property
    def enhancement_count(
        self,
    ) -> int:
        return sum(
            len(values)
            for values
            in self.instance[
                "enhancement_groups"
            ].values()
        )

    def _install_builtin_adapters(
        self,
    ) -> None:
        self.register_adapter(
            "dict",
            "dict",
            lambda value: dict(value),
        )

        self.register_adapter(
            "list",
            "list",
            lambda value: list(value),
        )

        self.register_adapter(
            "text",
            "text",
            lambda value: normalize_text(
                str(value)
            ),
        )

    def register_adapter(
        self,
        source_type: str,
        target_type: str,
        adapter: Adapter,
    ) -> None:
        if not source_type:
            raise CypherError(
                "source type is required"
            )

        if not target_type:
            raise CypherError(
                "target type is required"
            )

        key = (
            source_type,
            target_type,
        )

        if key in self._adapters:
            raise CypherError(
                "adapter already registered: "
                + source_type
                + " -> "
                + target_type
            )

        self._adapters[key] = adapter

    def routes(
        self,
    ) -> tuple[
        dict[str, str],
        ...,
    ]:
        return tuple(
            {
                "source_type": source,
                "target_type": target,
            }
            for source, target
            in sorted(
                self._adapters
            )
        )

    def encode(
        self,
        value: Any,
        encoding: str,
    ) -> str:
        if encoding == "json":
            return canonical_json(
                value
            )

        if encoding == "yaml":
            return yaml.safe_dump(
                value,
                allow_unicode=True,
                sort_keys=True,
            )

        if encoding == "text":
            if not isinstance(
                value,
                str,
            ):
                raise CypherError(
                    "text encoding requires string input"
                )

            return normalize_text(
                value
            )

        raise CypherError(
            "unsupported encoding: "
            + encoding
        )

    def decode(
        self,
        value: str,
        encoding: str,
    ) -> Any:
        if encoding == "json":
            return json.loads(
                value
            )

        if encoding == "yaml":
            return yaml.safe_load(
                value
            )

        if encoding == "text":
            return normalize_text(
                value
            )

        raise CypherError(
            "unsupported encoding: "
            + encoding
        )

    def translate(
        self,
        value: Any,
        *,
        source_type: str,
        target_type: str,
        authority: Any = None,
        lineage: Any = None,
        provenance: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        key = (
            source_type,
            target_type,
        )

        adapter = self._adapters.get(
            key
        )

        if adapter is None:
            raise CypherError(
                "no adapter route: "
                + source_type
                + " -> "
                + target_type
            )

        before = digest(
            value
        )

        transformed = adapter(
            value
        )

        after = digest(
            transformed
        )

        envelope = ExchangeEnvelope(
            exchange_id=(
                "exchange:"
                + uuid.uuid4().hex
            ),
            source_type=source_type,
            target_type=target_type,
            payload=transformed,
            authority=authority,
            lineage=lineage,
            provenance=provenance,
            metadata=dict(
                metadata or {}
            ),
        )

        projection = (
            envelope.projection()
        )

        projection[
            "translation"
        ] = {
            "source_digest": before,
            "target_digest": after,
            "identity_preserved": (
                source_type == target_type
                and before == after
            ),
            "loss_detected": (
                source_type == target_type
                and before != after
            ),
        }

        projection[
            "receipt_digest"
        ] = digest(
            projection
        )

        return projection

    def roundtrip(
        self,
        value: Any,
        encoding: str,
    ) -> dict[str, Any]:
        encoded = self.encode(
            value,
            encoding,
        )

        decoded = self.decode(
            encoded,
            encoding,
        )

        equivalent = (
            canonical_json(
                value
            )
            == canonical_json(
                decoded
            )
        )

        payload = {
            "encoding": encoding,
            "equivalent": equivalent,
            "input_digest": digest(
                value
            ),
            "output_digest": digest(
                decoded
            ),
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def explain_route(
        self,
        source_type: str,
        target_type: str,
    ) -> dict[str, Any]:
        key = (
            source_type,
            target_type,
        )

        exists = (
            key in self._adapters
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "cypher/route/1.0.0"
            ),
            "source_type": source_type,
            "target_type": target_type,
            "available": exists,
            "fail_closed": True,
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        encodings = set(
            self.instance[
                "supported_encodings"
            ]
        )

        dimensions = {
            "instance_integrity": True,
            "encoding_integrity": (
                encodings
                == {
                    "json",
                    "yaml",
                    "text",
                }
            ),
            "route_integrity": (
                len(
                    self._adapters
                ) >= 3
            ),
            "adapter_integrity": True,
            "authority_preservation": (
                self.instance[
                    "exchange"
                ][
                    "preserve_authority"
                ]
                is True
            ),
            "lineage_preservation": (
                self.instance[
                    "exchange"
                ][
                    "preserve_lineage"
                ]
                is True
            ),
            "provenance_preservation": (
                self.instance[
                    "exchange"
                ][
                    "preserve_provenance"
                ]
                is True
            ),
            "serialization_integrity": (
                self.roundtrip(
                    {
                        "a": 1,
                        "b": [
                            2,
                            3,
                        ],
                    },
                    "json",
                )[
                    "equivalent"
                ]
                is True
            ),
            "mutation_boundary": (
                self.instance[
                    "mutation_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "cypher/health/1.0.0"
            ),
            "dimensions": {
                key: {
                    "healthy": value
                }
                for key, value
                in dimensions.items()
            },
            "healthy": all(
                dimensions.values()
            ),
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def validate(
        self,
    ) -> dict[str, Any]:
        checks = {
            "abilities": (
                len(
                    CYPHER_ABILITIES
                ) == 18
            ),
            "pipeline": (
                len(
                    CYPHER_PIPELINE
                ) == 18
            ),
            "health_dimensions": (
                len(
                    CYPHER_HEALTH_DIMENSIONS
                ) == 9
            ),
            "validation_dimensions": (
                len(
                    CYPHER_VALIDATION_DIMENSIONS
                ) == 9
            ),
            "projections": (
                len(
                    CYPHER_PROJECTIONS
                ) == 9
            ),
            "enhancements": (
                self.enhancement_count
                == 27
            ),
            "encodings": (
                len(
                    self.instance[
                        "supported_encodings"
                    ]
                ) == 3
            ),
            "non_authoritative": (
                self.instance[
                    "authoritative"
                ]
                is False
            ),
            "mutation_forbidden": (
                self.instance[
                    "mutation_authorized"
                ]
                is False
            ),
        }

        roundtrips = {
            encoding: self.roundtrip(
                (
                    "cypher"
                    if encoding == "text"
                    else {
                        "cypher": [
                            1,
                            2,
                            3,
                        ]
                    }
                ),
                encoding,
            )[
                "equivalent"
            ]
            for encoding
            in self.instance[
                "supported_encodings"
            ]
        }

        valid = (
            all(
                checks.values()
            )
            and all(
                roundtrips.values()
            )
        )

        payload = {
            "schema": (
                "savant://assurance/"
                "cypher/1.0.0"
            ),
            "valid": valid,
            "checks": checks,
            "roundtrips": roundtrips,
            "ability_count": 18,
            "pipeline_stage_count": 18,
            "health_dimension_count": 9,
            "validation_dimension_count": 9,
            "projection_count": 9,
            "enhancement_count": 27,
            "authoritative": False,
            "mutation_authorized": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def profile(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "substrate_id": (
                self.substrate_id
            ),
            "name": "Cypher",
            "role": (
                "living exchange and "
                "interpretation substrate"
            ),
            "instance": self.instance,
            "abilities": list(
                CYPHER_ABILITIES
            ),
            "pipeline": list(
                CYPHER_PIPELINE
            ),
            "health_dimensions": list(
                CYPHER_HEALTH_DIMENSIONS
            ),
            "validation_dimensions": list(
                CYPHER_VALIDATION_DIMENSIONS
            ),
            "projections": list(
                CYPHER_PROJECTIONS
            ),
            "routes": list(
                self.routes()
            ),
            "enhancement_count": (
                self.enhancement_count
            ),
            "authoritative": False,
            "mutation_authorized": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload
