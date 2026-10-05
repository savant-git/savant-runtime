from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


schema = (
    "savant://runtime/urge/"
    "workbench-projection/1.0.0"
)

owner = "exile:urge"


class workbench_projection_error(
    ValueError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise workbench_projection_error(
            "workbench value must be "
            "canonical-json serializable"
        ) from exc


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise workbench_projection_error(
            "expected a mapping"
        )

    return dict(
        value
    )


def project(
    *,
    iteration: Mapping[
        str,
        Any,
    ] | None = None,
    creative: Mapping[
        str,
        Any,
    ] | None = None,
    logo: Mapping[
        str,
        Any,
    ] | None = None,
    renderer: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    iteration_data = _mapping(
        iteration
    )

    creative_data = _mapping(
        creative
    )

    logo_data = _mapping(
        logo
    )

    renderer_data = _mapping(
        renderer
    )

    iteration_body = (
        iteration_data.get(
            "iteration",
            iteration_data,
        )
        if iteration_data
        else {}
    )

    best = (
        iteration_body.get(
            "best"
        )
        if isinstance(
            iteration_body,
            Mapping,
        )
        else None
    )

    alternates = (
        iteration_body.get(
            "alternates",
            [],
        )
        if isinstance(
            iteration_body,
            Mapping,
        )
        else []
    )

    lineage = (
        iteration_body.get(
            "lineage",
            [],
        )
        if isinstance(
            iteration_body,
            Mapping,
        )
        else []
    )

    metrics = (
        iteration_body.get(
            "metrics",
            {},
        )
        if isinstance(
            iteration_body,
            Mapping,
        )
        else {}
    )

    frontier = creative_data.get(
        "frontier",
        [],
    )

    first_frontier = (
        creative_data.get(
            "first_frontier",
            [],
        )
    )

    discrimination = (
        creative_data.get(
            "final_discrimination",
            {},
        )
    )

    opus_lineage = []

    for event in creative_data.get(
        "lineage",
        [],
    ):
        if not isinstance(
            event,
            Mapping,
        ):
            continue

        opus_lineage.append(
            {
                "stage": event.get(
                    "stage"
                ),
                "lens": event.get(
                    "lens"
                ),
                "provider": event.get(
                    "provider"
                ),
                "model": event.get(
                    "model"
                ),
                "opus_lineage": (
                    event.get(
                        "opus_lineage",
                        {},
                    )
                ),
            }
        )

    result = {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "status": {
            "iteration": (
                "available"
                if iteration_data
                else "idle"
            ),
            "creative": (
                "available"
                if creative_data
                else "idle"
            ),
            "logo": (
                "available"
                if logo_data
                else "idle"
            ),
            "renderer": (
                renderer_data.get(
                    "state",
                    "reserved",
                )
                if renderer_data
                else "reserved"
            ),
        },
        "candidate_stage": {
            "best": best,
            "alternates": alternates,
        },
        "pressure": {
            "gaps": (
                best.get(
                    "assessment",
                    {},
                ).get(
                    "gaps",
                    [],
                )
                if isinstance(
                    best,
                    Mapping,
                )
                else []
            ),
            "stop_reason": (
                iteration_body.get(
                    "stop_reason"
                )
                if isinstance(
                    iteration_body,
                    Mapping,
                )
                else None
            ),
        },
        "creative_frontier": {
            "initial": (
                first_frontier
            ),
            "final": frontier,
            "discrimination": (
                discrimination
            ),
        },
        "logo": {
            "name": logo_data.get(
                "name"
            ),
            "brief_digest": (
                logo_data.get(
                    "brief_digest"
                )
            ),
            "stress_tests": (
                logo_data.get(
                    "stress_tests",
                    [],
                )
            ),
            "renderer_integration": (
                logo_data.get(
                    "renderer_integration",
                    {
                        "state": (
                            "reserved"
                        )
                    },
                )
            ),
        },
        "renderer": (
            renderer_data
            if renderer_data
            else {
                "state": "reserved",
                "renderer": {
                    "id": (
                        "savant-svg-renderer"
                    ),
                    "status": (
                        "not-integrated"
                    ),
                },
            }
        ),
        "lineage": {
            "iteration": lineage,
            "opus": opus_lineage,
        },
        "metrics": metrics,
        "ownership": {
            "iteration": (
                "exile:urge"
            ),
            "provider_orchestration": (
                "exile:opus"
            ),
            "structural_discrimination": (
                "exile:underscore"
            ),
            "renderer": (
                "savant-svg-renderer"
            ),
        },
        "boundaries": {
            "creates_authority": False,
            "mutates_canon": False,
            "mutates_source": False,
            "owns_provider_routing": False,
            "owns_underscore": False,
            "owns_renderer": False,
        },
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


__all__ = [
    "project",
    "workbench_projection_error",
]
