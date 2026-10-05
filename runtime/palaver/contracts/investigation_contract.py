#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import datetime, timezone
from typing import Any, Mapping

from runtime.lineage.model import stable_hash


@dataclass(slots=True)
class InvestigationPacket:
    id: str
    title: str
    objective: str

    status: str = "complete"
    created_at: str = field(
        default_factory=lambda: (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    )

    source_runtime_hash: str = ""
    source_lineage_hash: str = ""
    source_authority_hash: str = ""

    starting_nodes: list[str] = field(
        default_factory=list
    )

    traversed_nodes: list[str] = field(
        default_factory=list
    )

    traversed_edges: list[str] = field(
        default_factory=list
    )

    authority_sources: list[str] = field(
        default_factory=list
    )

    dependencies: list[str] = field(
        default_factory=list
    )

    contradictions: list[str] = field(
        default_factory=list
    )

    uncertainty_regions: list[str] = field(
        default_factory=list
    )

    recovery_routes: list[str] = field(
        default_factory=list
    )

    traversal: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    notes: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    deterministic_hash: str = ""

    def deterministic_core(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": (
                "savant."
                "investigation_packet.v2"
            ),
            "id": self.id,
            "title": self.title,
            "objective": self.objective,
            "status": self.status,
            "source_runtime_hash": (
                self.source_runtime_hash
            ),
            "source_lineage_hash": (
                self.source_lineage_hash
            ),
            "source_authority_hash": (
                self.source_authority_hash
            ),
            "starting_nodes": sorted(
                set(
                    self.starting_nodes
                )
            ),
            "traversed_nodes": sorted(
                set(
                    self.traversed_nodes
                )
            ),
            "traversed_edges": sorted(
                set(
                    self.traversed_edges
                )
            ),
            "authority_sources": sorted(
                set(
                    self.authority_sources
                )
            ),
            "dependencies": sorted(
                set(
                    self.dependencies
                )
            ),
            "contradictions": sorted(
                set(
                    self.contradictions
                )
            ),
            "uncertainty_regions": sorted(
                set(
                    self.uncertainty_regions
                )
            ),
            "recovery_routes": sorted(
                set(
                    self.recovery_routes
                )
            ),
            "traversal": deepcopy(
                self.traversal
            ),
            "notes": deepcopy(
                self.notes
            ),
            "metadata": deepcopy(
                self.metadata
            ),
        }

    def finalize(
        self,
    ) -> "InvestigationPacket":
        self.starting_nodes = sorted(
            set(
                self.starting_nodes
            )
        )

        self.traversed_nodes = sorted(
            set(
                self.traversed_nodes
            )
        )

        self.traversed_edges = sorted(
            set(
                self.traversed_edges
            )
        )

        self.authority_sources = sorted(
            set(
                self.authority_sources
            )
        )

        self.dependencies = sorted(
            set(
                self.dependencies
            )
        )

        self.contradictions = sorted(
            set(
                self.contradictions
            )
        )

        self.uncertainty_regions = sorted(
            set(
                self.uncertainty_regions
            )
        )

        self.recovery_routes = sorted(
            set(
                self.recovery_routes
            )
        )

        self.deterministic_hash = stable_hash(
            self.deterministic_core()
        )

        return self

    def to_dict(
        self,
    ) -> dict[str, Any]:
        if not self.deterministic_hash:
            self.finalize()

        payload = asdict(
            self
        )

        payload[
            "schema"
        ] = (
            "savant."
            "investigation_packet.v2"
        )

        return payload

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[
            str,
            Any,
        ],
    ) -> "InvestigationPacket":
        allowed = {
            field_name
            for field_name
            in cls.__dataclass_fields__
        }

        kwargs = {
            key: deepcopy(
                item
            )
            for key, item
            in value.items()
            if key in allowed
        }

        return cls(
            **kwargs
        )
