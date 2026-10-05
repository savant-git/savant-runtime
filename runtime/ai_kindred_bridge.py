#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ai_capabilities import (
    AICapabilityError,
    AICapabilityRegistry,
)
from runtime.ai_eligibility import AIEligibility

from lexicon.kindred.discipline_engine import (
    DisciplineEngine,
    DisciplineError,
    KindredEdge,
)


DEFAULT_EXILE_AUTHORITY = (
    ROOT
    / "canon-system"
    / "authority"
    / "exiles"
)


class AIKindredBridgeError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise AIKindredBridgeError(
            "PyYAML is required by the existing Savant YAML surface"
        ) from exc

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise AIKindredBridgeError(
            f"authority file must contain an object: {path}"
        )

    return data


def _canonical_element_id(
    record: Mapping[str, Any],
    path: Path,
) -> str:
    value = str(
        record.get(
            "id",
            "",
        )
    ).strip()

    return (
        value
        if value
        else f"exile:{path.stem}"
    )


class AIKindredBridge:
    def __init__(
        self,
        ai_registry: AICapabilityRegistry | None = None,
        kindred: DisciplineEngine | None = None,
    ) -> None:
        self.ai = (
            ai_registry
            or AICapabilityRegistry()
        )
        self.eligibility = AIEligibility(
            self.ai
        )
        self.kindred = (
            kindred
            or DisciplineEngine()
        )

    def provider_edges(
        self,
    ) -> list[KindredEdge]:
        edges: list[KindredEdge] = []

        for provider, state in (
            self.ai.provider_states().items()
        ):
            provider_id = (
                f"provider:{provider}"
            )

            for capability in (
                state.capabilities
            ):
                edges.append(
                    KindredEdge(
                        subject=provider_id,
                        relation="relation:provides",
                        object=(
                            "capability:ai:"
                            f"{capability}"
                        ),
                        basis=(
                            "ai-capability-registry"
                        ),
                        authority_state=(
                            "projected"
                        ),
                        provenance={
                            "source": str(
                                self.ai.config_path
                            ),
                        },
                        metadata={
                            "active": (
                                state.usable
                            ),
                            "provider": (
                                provider
                            ),
                        },
                    )
                )

        return edges

    def element_edges(
        self,
        element_id: str,
        record: Mapping[str, Any],
    ) -> list[KindredEdge]:
        resolved = (
            self.eligibility.resolve(
                record
            )
        )

        if not resolved["eligible"]:
            return []

        edges: list[KindredEdge] = []

        for capability in resolved[
            "declared_capabilities"
        ]:
            edges.append(
                KindredEdge(
                    subject=element_id,
                    relation=(
                        "relation:capable_of"
                    ),
                    object=(
                        "capability:ai:"
                        f"{capability}"
                    ),
                    basis=(
                        "element-ai-contract"
                    ),
                    authority_state=(
                        "projected"
                    ),
                    provenance={
                        "source": (
                            "element-ai-contract"
                        ),
                    },
                    metadata={
                        "active": (
                            capability
                            in resolved[
                                "usable_capabilities"
                            ]
                        ),
                        "native_fallback": (
                            resolved[
                                "native_operational"
                            ]
                        ),
                    },
                )
            )

        return edges

    def authority_file_edges(
        self,
        path: Path,
    ) -> list[KindredEdge]:
        record = _load_yaml(path)

        return self.element_edges(
            _canonical_element_id(
                record,
                path,
            ),
            record,
        )

    def scan_authority(
        self,
        authority_root: Path = (
            DEFAULT_EXILE_AUTHORITY
        ),
    ) -> list[KindredEdge]:
        if not authority_root.exists():
            raise AIKindredBridgeError(
                "authority root not found: "
                f"{authority_root}"
            )

        edges: list[KindredEdge] = []

        for path in sorted(
            authority_root.glob(
                "*.yaml"
            )
        ):
            edges.extend(
                self.authority_file_edges(
                    path
                )
            )

        return edges

    def projection(
        self,
        authority_root: Path = (
            DEFAULT_EXILE_AUTHORITY
        ),
    ) -> dict[str, Any]:
        direct_edges = [
            *self.provider_edges(),
            *self.scan_authority(
                authority_root
            ),
        ]

        projected = (
            self.kindred.project_edges(
                direct_edges,
                include_inverses=True,
            )
        )

        return {
            "schema": (
                "savant.ai-kindred-capabilities.v1"
            ),
            "mode": self.ai.mode(),
            "authority_effect": "none",
            "mutation_effect": "none",
            "provider_count": len(
                self.ai.provider_states()
            ),
            "usable_provider_count": len(
                self.ai.usable_providers()
            ),
            "edge_count": len(
                projected
            ),
            "edges": projected,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="savant-ai-kindred"
    )

    parser.add_argument(
        "--authority-root",
        default=str(
            DEFAULT_EXILE_AUTHORITY
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("project")
    sub.add_parser("validate")

    args = parser.parse_args()

    try:
        bridge = AIKindredBridge()

        projection = bridge.projection(
            Path(
                args.authority_root
            ).resolve()
        )

        if args.command == "validate":
            print(
                json.dumps(
                    {
                        "valid": True,
                        "mode": (
                            projection[
                                "mode"
                            ]
                        ),
                        "provider_count": (
                            projection[
                                "provider_count"
                            ]
                        ),
                        "usable_provider_count": (
                            projection[
                                "usable_provider_count"
                            ]
                        ),
                        "edge_count": (
                            projection[
                                "edge_count"
                            ]
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        print(
            json.dumps(
                projection,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 0

    except (
        AIKindredBridgeError,
        AICapabilityError,
        DisciplineError,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
