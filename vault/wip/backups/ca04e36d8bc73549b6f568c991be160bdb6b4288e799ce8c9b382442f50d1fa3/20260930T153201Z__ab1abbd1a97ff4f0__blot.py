#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import html
import json
from collections import defaultdict
from typing import Any

from .shard_ir import (
    ShardProgram,
    canonical_json,
)


schema = "savant.translucent.blot.v1"
authority_effect = "none"

MAX_RENDER_SHARDS = 25_000
MAX_RENDER_SEGUES = 75_000


class BlotError(
    ValueError
):
    pass


def _esc(
    value: Any,
) -> str:
    return html.escape(
        str(
            value
        ),
        quote=True,
    )


def _safe_id(
    value: str,
) -> str:
    out: list[
        str
    ] = []

    for char in str(
        value
    ):
        out.append(
            char
            if (
                char.isalnum()
                or char
                in "_-"
            )
            else "-"
        )

    result = "".join(
        out
    ).strip(
        "-"
    )

    return (
        result
        or "item"
    )


def _short(
    value: str,
    limit: int = 44,
) -> str:
    text = str(
        value
    )

    if (
        len(
            text
        )
        <= limit
    ):
        return text

    return (
        text[
            :limit - 1
        ]
        + "…"
    )


def _point_layout(
    program: ShardProgram,
    width: int,
) -> dict[
    str,
    tuple[
        float,
        float,
    ],
]:
    by_kind: dict[
        str,
        list[
            str
        ],
    ] = defaultdict(
        list
    )

    for shard in program.shards:
        by_kind[
            shard.kind
        ].append(
            shard.id
        )

    kinds = sorted(
        by_kind
    )

    x_margin = 90.0
    y_margin = 90.0

    usable = max(
        1.0,
        float(
            width
        )
        - x_margin
        * 2.0,
    )

    points: dict[
        str,
        tuple[
            float,
            float,
        ],
    ] = {}

    for (
        row,
        kind,
    ) in enumerate(
        kinds
    ):
        identities = sorted(
            by_kind[
                kind
            ]
        )

        step = (
            usable
            / max(
                1,
                len(
                    identities
                ),
            )
        )

        for (
            column,
            identity,
        ) in enumerate(
            identities
        ):
            points[
                identity
            ] = (
                x_margin
                + step
                * (
                    column
                    + 0.5
                ),
                y_margin
                + row
                * 150.0,
            )

    return points


def _symbol_for_kind(
    kind: str,
) -> str:
    safe = _safe_id(
        kind
    )

    kind_digest = (
        hashlib.sha256(
            kind.encode(
                "utf-8"
            )
        ).hexdigest()[
            :10
        ]
    )

    return (
        "blot-kind-"
        + safe
        + "-"
        + kind_digest
    )


class BlotRenderer:
    """
    Deterministic SVG projector for Translucent
    shard programs.

    Blot renders structure. It never becomes
    semantic authority.

    Reusable visual substance is defined once as
    SVG symbols and instanced with <use>.
    """

    def render(
        self,
        program: ShardProgram,
        *,
        width: int = 1600,
        row_height: int = 150,
        title: str = (
            "translucent shard graph"
        ),
    ) -> dict[
        str,
        Any,
    ]:
        if (
            len(
                program.shards
            )
            > MAX_RENDER_SHARDS
        ):
            raise BlotError(
                "render shard count exceeds "
                f"{MAX_RENDER_SHARDS}"
            )

        if (
            len(
                program.segues
            )
            > MAX_RENDER_SEGUES
        ):
            raise BlotError(
                "render segue count exceeds "
                f"{MAX_RENDER_SEGUES}"
            )

        if (
            width < 320
            or width > 16_384
        ):
            raise BlotError(
                "width must be between "
                "320 and 16384"
            )

        if (
            row_height < 80
            or row_height > 600
        ):
            raise BlotError(
                "row_height must be between "
                "80 and 600"
            )

        points = _point_layout(
            program,
            width,
        )

        kinds = sorted(
            {
                item.kind
                for item
                in program.shards
            }
        )

        rows = max(
            1,
            len(
                kinds
            ),
        )

        height = int(
            180
            + rows
            * row_height
        )

        metadata = {
            "schema":
                schema,

            "program_semantic_digest":
                program.semantic_digest,

            "program_source_digest":
                program.source_digest,

            "semantic_shard":
                "lex:primitive:shard",

            "semantic_segue":
                "lex:core:segue",

            "projection":
                "lex:core:wavre",

            "renderer":
                "blot",

            "renderer_semantic":
                "lex:projection:blot",

            "authority_effect":
                authority_effect,
        }

        parts: list[
            str
        ] = []

        parts.append(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{width}" '
                f'height="{height}" '
                f'viewBox="0 0 {width} {height}" '
                'role="img" '
                'aria-labelledby="blot-title blot-desc">'
            )
        )

        parts.append(
            (
                '<title id="blot-title">'
                + _esc(
                    title
                )
                + "</title>"
            )
        )

        parts.append(
            (
                '<desc id="blot-desc">'
                "deterministic non-authoritative "
                "projection of a translucent "
                "shard program"
                "</desc>"
            )
        )

        parts.append(
            '<metadata id="blot-metadata">'
        )

        parts.append(
            _esc(
                canonical_json(
                    metadata
                )
            )
        )

        parts.append(
            "</metadata>"
        )

        parts.append(
            "<defs>"
        )

        parts.append(
            (
                '<marker id="blot-arrow" '
                'markerWidth="8" '
                'markerHeight="8" '
                'refX="7" '
                'refY="4" '
                'orient="auto" '
                'markerUnits="strokeWidth">'
                '<path d="M0,0 L8,4 L0,8 z"/>'
                "</marker>"
            )
        )

        for kind in kinds:
            symbol = (
                _symbol_for_kind(
                    kind
                )
            )

            parts.append(
                (
                    f'<symbol id="{_esc(symbol)}" '
                    'viewBox="-54 -32 108 64">'
                )
            )

            parts.append(
                (
                    '<rect x="-52" y="-30" '
                    'width="104" height="60" '
                    'rx="16" '
                    'fill="currentColor" '
                    'fill-opacity="0.08" '
                    'stroke="currentColor" '
                    'stroke-width="1.5"/>'
                )
            )

            parts.append(
                (
                    '<circle cx="-36" cy="0" '
                    'r="6" '
                    'fill="currentColor"/>'
                )
            )

            parts.append(
                "</symbol>"
            )

        parts.append(
            "</defs>"
        )

        parts.append(
            '<g id="blot-segues" fill="none">'
        )

        for segue in sorted(
            program.segues,
            key=lambda item: item.id,
        ):
            (
                sx,
                sy,
            ) = points[
                segue.source
            ]

            (
                tx,
                ty,
            ) = points[
                segue.target
            ]

            dy = max(
                40.0,
                abs(
                    ty
                    - sy
                )
                * 0.45,
            )

            path = (
                f"M {sx:.2f} {sy:.2f} "
                f"C {sx:.2f} {sy + dy:.2f}, "
                f"{tx:.2f} {ty - dy:.2f}, "
                f"{tx:.2f} {ty:.2f}"
            )

            parts.append(
                (
                    f'<path id="{_esc(_safe_id(segue.id))}" '
                    f'd="{path}" '
                    'stroke="currentColor" '
                    'stroke-opacity="0.34" '
                    'stroke-width="1.5" '
                    'marker-end="url(#blot-arrow)" '
                    f'data-segue="{_esc(segue.id)}" '
                    f'data-relation="{_esc(segue.relation)}"/>'
                )
            )

        parts.append(
            "</g>"
        )

        parts.append(
            '<g id="blot-shards">'
        )

        for shard in sorted(
            program.shards,
            key=lambda item: item.id,
        ):
            (
                x,
                y,
            ) = points[
                shard.id
            ]

            symbol = (
                _symbol_for_kind(
                    shard.kind
                )
            )

            safe_id = (
                _safe_id(
                    shard.id
                )
            )

            parts.append(
                (
                    f'<g id="{_esc(safe_id)}" '
                    f'transform="translate({x:.2f} {y:.2f})" '
                    f'data-shard="{_esc(shard.id)}" '
                    f'data-kind="{_esc(shard.kind)}" '
                    f'data-truth="{_esc(shard.truth)}" '
                    f'data-digest="{_esc(shard.digest)}">'
                )
            )

            parts.append(
                (
                    f'<use href="#{_esc(symbol)}" '
                    'x="-54" y="-32" '
                    'width="108" height="64" '
                    'style="color:currentColor"/>'
                )
            )

            parts.append(
                (
                    '<text x="0" y="-4" '
                    'text-anchor="middle" '
                    'font-size="12" '
                    'font-family="ui-monospace, monospace">'
                    + _esc(
                        _short(
                            shard.id
                        )
                    )
                    + "</text>"
                )
            )

            parts.append(
                (
                    '<text x="0" y="14" '
                    'text-anchor="middle" '
                    'font-size="9" '
                    'opacity="0.62" '
                    'font-family="ui-monospace, monospace">'
                    + _esc(
                        shard.kind
                    )
                    + "</text>"
                )
            )

            parts.append(
                "</g>"
            )

        parts.append(
            "</g>"
        )

        parts.append(
            "</svg>"
        )

        svg = "".join(
            parts
        )

        source_map = {
            identity: {
                "x":
                    x,

                "y":
                    y,
            }
            for identity, (
                x,
                y,
            )
            in sorted(
                points.items()
            )
        }

        return {
            "schema":
                schema,

            "renderer":
                "blot",

            "mime_type":
                "image/svg+xml",

            "svg":
                svg,

            "svg_digest":
                hashlib.sha256(
                    svg.encode(
                        "utf-8"
                    )
                ).hexdigest(),

            "program_semantic_digest":
                program.semantic_digest,

            "source_map":
                source_map,

            "projection_only":
                True,

            "authority_effect":
                authority_effect,
        }


def render(
    program: ShardProgram,
    **kwargs: Any,
) -> dict[
    str,
    Any,
]:
    return (
        BlotRenderer()
        .render(
            program,
            **kwargs,
        )
    )


def selftest() -> dict[
    str,
    Any,
]:
    from .lucid import (
        LucidCompiler,
    )

    source = """lucid 1
@a :: data
  with value = 1
@b :: projection
  bind source -> @a
  needs @a
@a => @b :: projects
"""

    program = (
        LucidCompiler()
        .compile(
            source
        )
    )

    first = render(
        program
    )

    second = render(
        program
    )

    checks = {
        "authority_none":
            (
                authority_effect
                == "none"
            ),

        "stable_svg":
            (
                first[
                    "svg_digest"
                ]
                == second[
                    "svg_digest"
                ]
            ),

        "symbol_reuse":
            (
                "<symbol"
                in first[
                    "svg"
                ]
                and "<use"
                in first[
                    "svg"
                ]
            ),

        "segue_projected":
            (
                'data-relation="projects"'
                in first[
                    "svg"
                ]
            ),

        "metadata_bound":
            (
                program.semantic_digest
                in first[
                    "svg"
                ]
            ),

        "projection_only":
            (
                first[
                    "projection_only"
                ]
                is True
            ),
    }

    return {
        "schema":
            (
                "savant.translucent."
                "blot-selftest.v1"
            ),

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "svg_digest":
            first[
                "svg_digest"
            ],

        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
