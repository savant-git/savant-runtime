from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping


schema = "savant://runtime/urge/renderer-slot/1.0.0"
owner = "exile:urge"


class renderer_slot_error(
    RuntimeError
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
        raise renderer_slot_error(
            "renderer projection must be canonical-json serializable"
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


@dataclass(
    frozen=True,
    slots=True,
)
class renderer_binding:
    id: str
    project: Callable[
        [
            Mapping[
                str,
                Any,
            ]
        ],
        Mapping[
            str,
            Any,
        ],
    ]
    media_type: str = (
        "image/svg+xml"
    )
    owner: str = (
        "savant-svg-renderer"
    )

    def __post_init__(
        self,
    ) -> None:
        if not str(
            self.id
        ).strip():
            raise renderer_slot_error(
                "renderer binding id is required"
            )

        if not callable(
            self.project
        ):
            raise renderer_slot_error(
                "renderer project must be callable"
            )

        if not str(
            self.owner
        ).strip():
            raise renderer_slot_error(
                "renderer owner is required"
            )


def project(
    *,
    candidate: Mapping[
        str,
        Any,
    ],
    binding: renderer_binding
    | None = None,
    context: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    if not isinstance(
        candidate,
        Mapping,
    ):
        raise renderer_slot_error(
            "candidate must be a mapping"
        )

    candidate_projection = dict(
        candidate
    )

    candidate_digest = _digest(
        candidate_projection
    )

    if binding is None:
        result = {
            "schema": schema,
            "owner": owner,
            "state": "reserved",
            "candidate_digest": (
                candidate_digest
            ),
            "renderer": {
                "id": (
                    "savant-svg-renderer"
                ),
                "binding": None,
                "status": (
                    "not-integrated"
                ),
            },
            "authority_effect": "none",
            "projection_only": True,
            "boundaries": {
                "owns_renderer": False,
                "mutates_candidate": False,
                "mutates_canon": False,
                "creates_authority": False,
            },
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        return result

    request = {
        "schema": schema,
        "operation": (
            "project-vector-candidate"
        ),
        "candidate": (
            candidate_projection
        ),
        "candidate_digest": (
            candidate_digest
        ),
        "context": dict(
            context
            or {}
        ),
        "requirements": {
            "preserve_semantics": True,
            "preserve_provenance": True,
            "deterministic_projection": True,
            "do_not_create_authority": True,
            "do_not_mutate_candidate": True,
        },
    }

    before = _digest(
        candidate_projection
    )

    rendered = binding.project(
        request
    )

    if inspect.isawaitable(
        rendered
    ):
        raise renderer_slot_error(
            "async renderer requires an async boundary"
        )

    if not isinstance(
        rendered,
        Mapping,
    ):
        raise renderer_slot_error(
            "renderer must return a mapping"
        )

    after = _digest(
        candidate_projection
    )

    if before != after:
        raise renderer_slot_error(
            "renderer mutated candidate projection"
        )

    rendered_projection = dict(
        rendered
    )

    result = {
        "schema": schema,
        "owner": owner,
        "state": "projected",
        "candidate_digest": (
            candidate_digest
        ),
        "renderer": {
            "id": binding.id,
            "owner": (
                binding.owner
            ),
            "media_type": (
                binding.media_type
            ),
        },
        "projection": (
            rendered_projection
        ),
        "projection_digest": (
            _digest(
                rendered_projection
            )
        ),
        "authority_effect": "none",
        "projection_only": True,
        "boundaries": {
            "owns_renderer": False,
            "mutates_candidate": False,
            "mutates_canon": False,
            "creates_authority": False,
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
    "renderer_binding",
    "renderer_slot_error",
]
