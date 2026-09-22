#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    CharacterState,
    GuiseError,
    digest,
)


class GuiseStateError(GuiseError):
    pass


@dataclass(frozen=True)
class StateOverlay:
    kind: str
    values: Mapping[str, Any]
    source_refs: tuple[str, ...] = ()
    temporal_ref: str | None = None
    relationship_ref: str | None = None
    epistemic_class: str = "hypothesis"

    def projection(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "values": dict(self.values),
            "source_refs": list(
                self.source_refs
            ),
            "temporal_ref": self.temporal_ref,
            "relationship_ref": (
                self.relationship_ref
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


class CharacterStateProjector:
    overlay_order = (
        "baseline",
        "phase",
        "temporal",
        "relationship",
        "knowledge",
        "physiological",
        "emotional",
        "pressure",
        "goal",
        "incentive",
        "recent_event",
        "deliberate_choice",
    )

    def project(
        self,
        graph: CharacterGraph,
        *,
        at: str | None = None,
        phase: str | None = None,
        overlays: Sequence[
            StateOverlay
        ] = (),
    ) -> dict[str, Any]:
        grouped: dict[
            str,
            list[StateOverlay],
        ] = {
            key: []
            for key in self.overlay_order
        }

        unknown = []

        for overlay in overlays:
            if overlay.kind not in grouped:
                unknown.append(
                    overlay.projection()
                )
                continue

            grouped[
                overlay.kind
            ].append(overlay)

        resolved: dict[str, Any] = {}
        provenance: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        conflicts = []

        for kind in self.overlay_order:
            for overlay in grouped[kind]:
                for key, value in (
                    overlay.values.items()
                ):
                    if (
                        key in resolved
                        and resolved[key] != value
                    ):
                        conflicts.append(
                            {
                                "field": key,
                                "previous": (
                                    resolved[key]
                                ),
                                "incoming": value,
                                "overlay_kind": (
                                    kind
                                ),
                                "resolution": (
                                    "preserved_as_"
                                    "state_conflict"
                                ),
                            }
                        )

                    resolved[key] = value

                    provenance.setdefault(
                        key,
                        [],
                    ).append(
                        overlay.projection()
                    )

        state = CharacterState(
            character_id=graph.character_id,
            at=at,
            phase=phase,
            relationship_state={
                key: value
                for key, value
                in resolved.items()
                if key.startswith(
                    "relationship."
                )
            },
            physiological={
                key: value
                for key, value
                in resolved.items()
                if key.startswith(
                    "physiological."
                )
            },
            emotional={
                key: value
                for key, value
                in resolved.items()
                if key.startswith(
                    "emotional."
                )
            },
            pressures=tuple(
                str(value)
                for key, value
                in resolved.items()
                if key.startswith(
                    "pressure."
                )
            ),
            goals=tuple(
                str(value)
                for key, value
                in resolved.items()
                if key.startswith(
                    "goal."
                )
            ),
            incentives=tuple(
                str(value)
                for key, value
                in resolved.items()
                if key.startswith(
                    "incentive."
                )
            ),
            recent_event_refs=tuple(
                str(value)
                for key, value
                in resolved.items()
                if key.startswith(
                    "recent_event."
                )
            ),
        )

        graph.add_state(state)

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "state_projection",
            "character_id": (
                graph.character_id
            ),
            "state": state.projection(),
            "resolved": resolved,
            "provenance": provenance,
            "conflicts": conflicts,
            "unknown_overlays": unknown,
            "overlay_order": list(
                self.overlay_order
            ),
            "mutates_authority": False,
            "authority_effect": "none",
        }

        projection[
            "projection_digest"
        ] = digest(projection)

        return projection
