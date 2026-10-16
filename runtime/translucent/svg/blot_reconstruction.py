#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

from runtime.translucent.blot_reconstruction import (
    ConstructionPrimitive,
    ExecutionContract,
)


name = "blot."
schema = "savant.translucent.svg.blot.reconstruction.v2"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

svg_ns = "http://www.w3.org/2000/svg"

max_svg_elements = 16384
max_path_commands = 32768
max_gradient_stops = 64
max_mask_elements = 256
max_clip_elements = 256
max_filter_elements = 128


class BlotSvgError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotSvgError(
            f"{field_name} is required"
        )

    return result


def _finite(
    value: Any,
    field_name: str,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BlotSvgError(
            f"{field_name} must be numeric"
        ) from exc

    if not math.isfinite(result):
        raise BlotSvgError(
            f"{field_name} must be finite"
        )

    return result


def _positive(
    value: Any,
    field_name: str,
) -> float:
    result = _finite(
        value,
        field_name,
    )

    if result <= 0.0:
        raise BlotSvgError(
            f"{field_name} must be positive"
        )

    return result


def _unit(
    value: Any,
    field_name: str,
) -> float:
    result = _finite(
        value,
        field_name,
    )

    if result < 0.0 or result > 1.0:
        raise BlotSvgError(
            f"{field_name} must be between 0 and 1"
        )

    return result


def _num(value: Any) -> str:
    number = _finite(
        value,
        "number",
    )

    if abs(number) < 0.000000000001:
        number = 0.0

    rounded = round(
        number,
        9,
    )

    if float(rounded).is_integer():
        return str(
            int(rounded)
        )

    return (
        f"{rounded:.9f}"
        .rstrip("0")
        .rstrip(".")
    )


def _safe_id(value: Any) -> str:
    raw = _text(
        value,
        "svg id",
    )

    result: list[str] = []

    for character in raw:
        if (
            character.isalnum()
            or character in "-_.:"
        ):
            result.append(character)
        else:
            result.append("-")

    safe = "".join(result).strip("-")

    if not safe:
        raise BlotSvgError(
            "svg id is empty after normalization"
        )

    if safe[0].isdigit():
        safe = f"blot-{safe}"

    return safe


def _unique_text(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if str(value).strip()
        )
    )


def _attrs(
    values: Mapping[str, Any],
) -> dict[str, str]:
    result: dict[str, str] = {}

    for key in sorted(values):
        value = values[key]

        if value is None:
            continue

        result[str(key)] = str(value)

    return result


def _svg_element(
    tag: str,
    attributes: Mapping[
        str,
        Any
    ] | None = None,
) -> ET.Element:
    return ET.Element(
        f"{{{svg_ns}}}{tag}",
        _attrs(
            attributes or {}
        ),
    )


@dataclass(frozen=True, slots=True)
class SvgStop:
    offset: float
    color: str
    opacity: float = 1.0

    def normalized(self) -> dict[str, Any]:
        body = {
            "offset":
                _unit(
                    self.offset,
                    "offset",
                ),

            "color":
                _text(
                    self.color,
                    "color",
                ),

            "opacity":
                _unit(
                    self.opacity,
                    "opacity",
                ),
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgLinearGradient:
    gradient_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    stops: tuple[SvgStop, ...]
    units: str = "userSpaceOnUse"
    transform: str | None = None

    def normalized(self) -> dict[str, Any]:
        if not self.stops:
            raise BlotSvgError(
                "linear gradient requires stops"
            )

        if len(self.stops) > max_gradient_stops:
            raise BlotSvgError(
                "gradient stop limit exceeded"
            )

        body = {
            "kind":
                "linear-gradient",

            "gradient_id":
                _safe_id(
                    self.gradient_id
                ),

            "x1":
                _finite(
                    self.x1,
                    "x1",
                ),

            "y1":
                _finite(
                    self.y1,
                    "y1",
                ),

            "x2":
                _finite(
                    self.x2,
                    "x2",
                ),

            "y2":
                _finite(
                    self.y2,
                    "y2",
                ),

            "stops":
                [
                    stop.normalized()
                    for stop in self.stops
                ],

            "units":
                _text(
                    self.units,
                    "units",
                ),

            "transform":
                self.transform,
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgRadialGradient:
    gradient_id: str
    cx: float
    cy: float
    r: float
    stops: tuple[SvgStop, ...]
    fx: float | None = None
    fy: float | None = None
    units: str = "userSpaceOnUse"
    transform: str | None = None

    def normalized(self) -> dict[str, Any]:
        if not self.stops:
            raise BlotSvgError(
                "radial gradient requires stops"
            )

        if len(self.stops) > max_gradient_stops:
            raise BlotSvgError(
                "gradient stop limit exceeded"
            )

        body = {
            "kind":
                "radial-gradient",

            "gradient_id":
                _safe_id(
                    self.gradient_id
                ),

            "cx":
                _finite(
                    self.cx,
                    "cx",
                ),

            "cy":
                _finite(
                    self.cy,
                    "cy",
                ),

            "r":
                _positive(
                    self.r,
                    "r",
                ),

            "fx":
                (
                    _finite(
                        self.fx,
                        "fx",
                    )
                    if self.fx is not None
                    else None
                ),

            "fy":
                (
                    _finite(
                        self.fy,
                        "fy",
                    )
                    if self.fy is not None
                    else None
                ),

            "stops":
                [
                    stop.normalized()
                    for stop in self.stops
                ],

            "units":
                _text(
                    self.units,
                    "units",
                ),

            "transform":
                self.transform,
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgPath:
    path_id: str
    d: str
    fill: str = "none"
    stroke: str | None = None
    stroke_width: float | None = None
    opacity: float = 1.0
    fill_rule: str = "nonzero"
    clip_path: str | None = None
    mask: str | None = None
    transform: str | None = None
    attributes: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        fill_rule = _text(
            self.fill_rule,
            "fill_rule",
        )

        if fill_rule not in {
            "nonzero",
            "evenodd",
        }:
            raise BlotSvgError(
                "fill_rule must be nonzero "
                "or evenodd"
            )

        body = {
            "kind":
                "path",

            "path_id":
                _safe_id(
                    self.path_id
                ),

            "d":
                _text(
                    self.d,
                    "d",
                ),

            "fill":
                _text(
                    self.fill,
                    "fill",
                ),

            "stroke":
                self.stroke,

            "stroke_width":
                (
                    _positive(
                        self.stroke_width,
                        "stroke_width",
                    )
                    if self.stroke_width
                    is not None
                    else None
                ),

            "opacity":
                _unit(
                    self.opacity,
                    "opacity",
                ),

            "fill_rule":
                fill_rule,

            "clip_path":
                self.clip_path,

            "mask":
                self.mask,

            "transform":
                self.transform,

            "attributes":
                dict(
                    self.attributes
                ),
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgClipPath:
    clip_id: str
    paths: tuple[SvgPath, ...]

    def normalized(self) -> dict[str, Any]:
        if not self.paths:
            raise BlotSvgError(
                "clip path requires geometry"
            )

        body = {
            "kind":
                "clip-path",

            "clip_id":
                _safe_id(
                    self.clip_id
                ),

            "paths":
                [
                    path.normalized()
                    for path in self.paths
                ],
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgMask:
    mask_id: str
    paths: tuple[SvgPath, ...]
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    mask_units: str = "userSpaceOnUse"

    def normalized(self) -> dict[str, Any]:
        if not self.paths:
            raise BlotSvgError(
                "mask requires geometry"
            )

        body = {
            "kind":
                "mask",

            "mask_id":
                _safe_id(
                    self.mask_id
                ),

            "paths":
                [
                    path.normalized()
                    for path in self.paths
                ],

            "x":
                (
                    _finite(
                        self.x,
                        "x",
                    )
                    if self.x is not None
                    else None
                ),

            "y":
                (
                    _finite(
                        self.y,
                        "y",
                    )
                    if self.y is not None
                    else None
                ),

            "width":
                (
                    _positive(
                        self.width,
                        "width",
                    )
                    if self.width is not None
                    else None
                ),

            "height":
                (
                    _positive(
                        self.height,
                        "height",
                    )
                    if self.height is not None
                    else None
                ),

            "mask_units":
                _text(
                    self.mask_units,
                    "mask_units",
                ),
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgGroup:
    group_id: str
    paths: tuple[SvgPath, ...]
    transform: str | None = None
    opacity: float = 1.0
    clip_path: str | None = None
    mask: str | None = None
    attributes: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        body = {
            "kind":
                "group",

            "group_id":
                _safe_id(
                    self.group_id
                ),

            "paths":
                [
                    path.normalized()
                    for path in self.paths
                ],

            "transform":
                self.transform,

            "opacity":
                _unit(
                    self.opacity,
                    "opacity",
                ),

            "clip_path":
                self.clip_path,

            "mask":
                self.mask,

            "attributes":
                dict(
                    self.attributes
                ),
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class SvgDocument:
    width: float
    height: float
    view_box: tuple[
        float,
        float,
        float,
        float,
    ]
    paths: tuple[SvgPath, ...] = ()
    groups: tuple[SvgGroup, ...] = ()
    linear_gradients: tuple[
        SvgLinearGradient,
        ...
    ] = ()
    radial_gradients: tuple[
        SvgRadialGradient,
        ...
    ] = ()
    clip_paths: tuple[
        SvgClipPath,
        ...
    ] = ()
    masks: tuple[
        SvgMask,
        ...
    ] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        if len(self.view_box) != 4:
            raise BlotSvgError(
                "view_box must contain "
                "four values"
            )

        view_box = tuple(
            _finite(
                value,
                "view_box",
            )
            for value in self.view_box
        )

        if view_box[2] <= 0:
            raise BlotSvgError(
                "view_box width must "
                "be positive"
            )

        if view_box[3] <= 0:
            raise BlotSvgError(
                "view_box height must "
                "be positive"
            )

        element_count = (
            len(self.paths)
            + sum(
                len(group.paths)
                for group in self.groups
            )
            + sum(
                len(clip.paths)
                for clip in self.clip_paths
            )
            + sum(
                len(mask.paths)
                for mask in self.masks
            )
        )

        if element_count > max_svg_elements:
            raise BlotSvgError(
                "svg element limit exceeded"
            )

        if (
            len(self.clip_paths)
            > max_clip_elements
        ):
            raise BlotSvgError(
                "clip path limit exceeded"
            )

        if len(self.masks) > max_mask_elements:
            raise BlotSvgError(
                "mask limit exceeded"
            )

        body = {
            "schema":
                f"{schema}.document",

            "width":
                _positive(
                    self.width,
                    "width",
                ),

            "height":
                _positive(
                    self.height,
                    "height",
                ),

            "view_box":
                list(view_box),

            "paths":
                [
                    path.normalized()
                    for path in self.paths
                ],

            "groups":
                [
                    group.normalized()
                    for group in self.groups
                ],

            "linear_gradients":
                [
                    gradient.normalized()
                    for gradient
                    in self.linear_gradients
                ],

            "radial_gradients":
                [
                    gradient.normalized()
                    for gradient
                    in self.radial_gradients
                ],

            "clip_paths":
                [
                    clip.normalized()
                    for clip in self.clip_paths
                ],

            "masks":
                [
                    mask.normalized()
                    for mask in self.masks
                ],

            "metadata":
                dict(
                    self.metadata
                ),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        return body

    def render(self) -> str:
        normalized = self.normalized()

        ET.register_namespace(
            "",
            svg_ns,
        )

        root = _svg_element(
            "svg",
            {
                "width":
                    _num(
                        normalized[
                            "width"
                        ]
                    ),

                "height":
                    _num(
                        normalized[
                            "height"
                        ]
                    ),

                "viewBox":
                    " ".join(
                        _num(value)
                        for value
                        in normalized[
                            "view_box"
                        ]
                    ),

                "version":
                    "1.1",

                "data-blot-schema":
                    schema,

                "data-blot-digest":
                    normalized[
                        "digest"
                    ],
            },
        )

        metadata = _svg_element(
            "metadata"
        )

        metadata.text = _canonical(
            {
                "schema":
                    schema,

                "projection":
                    normalized[
                        "metadata"
                    ],

                "authority_effect":
                    "none",

                "mutation_effect":
                    "none",

                "projection_only":
                    True,

                "document_digest":
                    normalized[
                        "digest"
                    ],
            }
        )

        root.append(metadata)

        defs = _svg_element(
            "defs"
        )

        for gradient in sorted(
            self.linear_gradients,
            key=lambda item:
                item.gradient_id,
        ):
            data = gradient.normalized()

            element = _svg_element(
                "linearGradient",
                {
                    "id":
                        data[
                            "gradient_id"
                        ],

                    "x1":
                        _num(
                            data[
                                "x1"
                            ]
                        ),

                    "y1":
                        _num(
                            data[
                                "y1"
                            ]
                        ),

                    "x2":
                        _num(
                            data[
                                "x2"
                            ]
                        ),

                    "y2":
                        _num(
                            data[
                                "y2"
                            ]
                        ),

                    "gradientUnits":
                        data[
                            "units"
                        ],

                    "gradientTransform":
                        data[
                            "transform"
                        ],
                },
            )

            for stop in data["stops"]:
                element.append(
                    _svg_element(
                        "stop",
                        {
                            "offset":
                                (
                                    _num(
                                        stop[
                                            "offset"
                                        ]
                                        * 100.0
                                    )
                                    + "%"
                                ),

                            "stop-color":
                                stop[
                                    "color"
                                ],

                            "stop-opacity":
                                _num(
                                    stop[
                                        "opacity"
                                    ]
                                ),
                        },
                    )
                )

            defs.append(element)

        for gradient in sorted(
            self.radial_gradients,
            key=lambda item:
                item.gradient_id,
        ):
            data = gradient.normalized()

            element = _svg_element(
                "radialGradient",
                {
                    "id":
                        data[
                            "gradient_id"
                        ],

                    "cx":
                        _num(
                            data[
                                "cx"
                            ]
                        ),

                    "cy":
                        _num(
                            data[
                                "cy"
                            ]
                        ),

                    "r":
                        _num(
                            data[
                                "r"
                            ]
                        ),

                    "fx":
                        (
                            _num(
                                data[
                                    "fx"
                                ]
                            )
                            if data[
                                "fx"
                            ]
                            is not None
                            else None
                        ),

                    "fy":
                        (
                            _num(
                                data[
                                    "fy"
                                ]
                            )
                            if data[
                                "fy"
                            ]
                            is not None
                            else None
                        ),

                    "gradientUnits":
                        data[
                            "units"
                        ],

                    "gradientTransform":
                        data[
                            "transform"
                        ],
                },
            )

            for stop in data["stops"]:
                element.append(
                    _svg_element(
                        "stop",
                        {
                            "offset":
                                (
                                    _num(
                                        stop[
                                            "offset"
                                        ]
                                        * 100.0
                                    )
                                    + "%"
                                ),

                            "stop-color":
                                stop[
                                    "color"
                                ],

                            "stop-opacity":
                                _num(
                                    stop[
                                        "opacity"
                                    ]
                                ),
                        },
                    )
                )

            defs.append(element)

        for clip in sorted(
            self.clip_paths,
            key=lambda item:
                item.clip_id,
        ):
            data = clip.normalized()

            element = _svg_element(
                "clipPath",
                {
                    "id":
                        data[
                            "clip_id"
                        ],
                },
            )

            for path in clip.paths:
                element.append(
                    _path_element(
                        path,
                        definition=True,
                    )
                )

            defs.append(element)

        for mask in sorted(
            self.masks,
            key=lambda item:
                item.mask_id,
        ):
            data = mask.normalized()

            element = _svg_element(
                "mask",
                {
                    "id":
                        data[
                            "mask_id"
                        ],

                    "maskUnits":
                        data[
                            "mask_units"
                        ],

                    "x":
                        (
                            _num(
                                data[
                                    "x"
                                ]
                            )
                            if data[
                                "x"
                            ]
                            is not None
                            else None
                        ),

                    "y":
                        (
                            _num(
                                data[
                                    "y"
                                ]
                            )
                            if data[
                                "y"
                            ]
                            is not None
                            else None
                        ),

                    "width":
                        (
                            _num(
                                data[
                                    "width"
                                ]
                            )
                            if data[
                                "width"
                            ]
                            is not None
                            else None
                        ),

                    "height":
                        (
                            _num(
                                data[
                                    "height"
                                ]
                            )
                            if data[
                                "height"
                            ]
                            is not None
                            else None
                        ),
                },
            )

            for path in mask.paths:
                element.append(
                    _path_element(
                        path,
                        definition=True,
                    )
                )

            defs.append(element)

        if len(defs):
            root.append(defs)

        for path in self.paths:
            root.append(
                _path_element(path)
            )

        for group in self.groups:
            root.append(
                _group_element(group)
            )

        return ET.tostring(
            root,
            encoding="unicode",
            short_empty_elements=True,
        )


def _path_element(
    path: SvgPath,
    *,
    definition: bool = False,
) -> ET.Element:
    data = path.normalized()

    attributes: dict[
        str,
        Any
    ] = {
        "id":
            data[
                "path_id"
            ],

        "d":
            data[
                "d"
            ],

        "fill":
            data[
                "fill"
            ],

        "fill-rule":
            data[
                "fill_rule"
            ],

        "opacity":
            _num(
                data[
                    "opacity"
                ]
            ),

        "transform":
            data[
                "transform"
            ],
    }

    if data["stroke"] is not None:
        attributes[
            "stroke"
        ] = data[
            "stroke"
        ]

    if data["stroke_width"] is not None:
        attributes[
            "stroke-width"
        ] = _num(
            data[
                "stroke_width"
            ]
        )

    if (
        not definition
        and data[
            "clip_path"
        ]
        is not None
    ):
        attributes[
            "clip-path"
        ] = (
            "url(#"
            + _safe_id(
                data[
                    "clip_path"
                ]
            )
            + ")"
        )

    if (
        not definition
        and data[
            "mask"
        ]
        is not None
    ):
        attributes[
            "mask"
        ] = (
            "url(#"
            + _safe_id(
                data[
                    "mask"
                ]
            )
            + ")"
        )

    for key, value in sorted(
        data[
            "attributes"
        ].items()
    ):
        if value is not None:
            attributes[
                str(key)
            ] = value

    return _svg_element(
        "path",
        attributes,
    )


def _group_element(
    group: SvgGroup,
) -> ET.Element:
    data = group.normalized()

    attributes: dict[
        str,
        Any
    ] = {
        "id":
            data[
                "group_id"
            ],

        "transform":
            data[
                "transform"
            ],

        "opacity":
            _num(
                data[
                    "opacity"
                ]
            ),
    }

    if data["clip_path"] is not None:
        attributes[
            "clip-path"
        ] = (
            "url(#"
            + _safe_id(
                data[
                    "clip_path"
                ]
            )
            + ")"
        )

    if data["mask"] is not None:
        attributes[
            "mask"
        ] = (
            "url(#"
            + _safe_id(
                data[
                    "mask"
                ]
            )
            + ")"
        )

    for key, value in sorted(
        data[
            "attributes"
        ].items()
    ):
        if value is not None:
            attributes[
                str(key)
            ] = value

    element = _svg_element(
        "g",
        attributes,
    )

    for path in group.paths:
        element.append(
            _path_element(path)
        )

    return element


def path_from_primitive(
    primitive: ConstructionPrimitive,
    *,
    fill: str = "none",
    stroke: str | None = None,
    stroke_width: float | None = None,
    opacity: float = 1.0,
) -> SvgPath:
    data = primitive.normalized()

    primitive_id = data[
        "primitive_id"
    ]

    kind = data[
        "kind"
    ]

    parameters = data[
        "parameters"
    ]

    if kind not in {
        "path",
        "closed-cubic-bezier",
        "open-cubic-bezier",
        "compound-path",
    }:
        raise BlotSvgError(
            "primitive cannot be projected "
            "as an svg path without an "
            "explicit path projection: "
            f"{kind}"
        )

    d = parameters.get("d")

    if not isinstance(d, str) or not d.strip():
        raise BlotSvgError(
            "path primitive requires "
            "parameters.d"
        )

    fill_rule = str(
        parameters.get(
            "fill_rule",
            "nonzero",
        )
    )

    transform = parameters.get(
        "transform"
    )

    clip_path = parameters.get(
        "clip_path"
    )

    mask = parameters.get(
        "mask"
    )

    return SvgPath(
        path_id=primitive_id,
        d=d,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        opacity=opacity,
        fill_rule=fill_rule,
        transform=(
            str(transform)
            if transform is not None
            else None
        ),
        clip_path=(
            str(clip_path)
            if clip_path is not None
            else None
        ),
        mask=(
            str(mask)
            if mask is not None
            else None
        ),
        attributes={
            "data-blot-primitive-kind":
                kind,

            "data-blot-primitive-digest":
                data[
                    "digest"
                ],

            "data-blot-truth-state":
                data[
                    "state"
                ],
        },
    )


class ProjectionBuilder:
    def __init__(
        self,
        contract: ExecutionContract,
        *,
        width: float,
        height: float,
        view_box: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
        profile: str = "presentation",
    ) -> None:
        contract_data = (
            contract.normalized()
        )

        if not contract_data[
            "execution_ready"
        ]:
            raise BlotSvgError(
                "svg projection requires "
                "execution_ready=true"
            )

        self.contract = contract
        self.width = _positive(
            width,
            "width",
        )
        self.height = _positive(
            height,
            "height",
        )

        self.view_box = (
            view_box
            if view_box is not None
            else (
                0.0,
                0.0,
                self.width,
                self.height,
            )
        )

        if len(self.view_box) != 4:
            raise BlotSvgError(
                "view_box must contain "
                "four values"
            )

        self.profile = _text(
            profile,
            "profile",
        )

        self._paths: dict[
            str,
            SvgPath,
        ] = {}

        self._groups: dict[
            str,
            SvgGroup,
        ] = {}

        self._linear_gradients: dict[
            str,
            SvgLinearGradient,
        ] = {}

        self._radial_gradients: dict[
            str,
            SvgRadialGradient,
        ] = {}

        self._clip_paths: dict[
            str,
            SvgClipPath,
        ] = {}

        self._masks: dict[
            str,
            SvgMask,
        ] = {}

        self._primitive_digests: dict[
            str,
            str,
        ] = {}

    def _insert(
        self,
        store: dict[str, Any],
        key: str,
        value: Any,
    ) -> str:
        existing = store.get(key)

        if existing is not None:
            if (
                existing.normalized()
                != value.normalized()
            ):
                raise BlotSvgError(
                    "projection identity conflict: "
                    f"{key}"
                )

            return key

        store[key] = value

        return key

    def add_path(
        self,
        path: SvgPath,
    ) -> str:
        key = path.normalized()[
            "path_id"
        ]

        return self._insert(
            self._paths,
            key,
            path,
        )

    def add_group(
        self,
        group: SvgGroup,
    ) -> str:
        key = group.normalized()[
            "group_id"
        ]

        return self._insert(
            self._groups,
            key,
            group,
        )

    def add_linear_gradient(
        self,
        gradient: SvgLinearGradient,
    ) -> str:
        key = gradient.normalized()[
            "gradient_id"
        ]

        return self._insert(
            self._linear_gradients,
            key,
            gradient,
        )

    def add_radial_gradient(
        self,
        gradient: SvgRadialGradient,
    ) -> str:
        key = gradient.normalized()[
            "gradient_id"
        ]

        return self._insert(
            self._radial_gradients,
            key,
            gradient,
        )

    def add_clip_path(
        self,
        clip_path: SvgClipPath,
    ) -> str:
        if (
            len(self._clip_paths)
            >= max_clip_elements
            and clip_path.clip_id
            not in self._clip_paths
        ):
            raise BlotSvgError(
                "clip path limit exceeded"
            )

        key = clip_path.normalized()[
            "clip_id"
        ]

        return self._insert(
            self._clip_paths,
            key,
            clip_path,
        )

    def add_mask(
        self,
        mask: SvgMask,
    ) -> str:
        if (
            len(self._masks)
            >= max_mask_elements
            and mask.mask_id
            not in self._masks
        ):
            raise BlotSvgError(
                "mask limit exceeded"
            )

        key = mask.normalized()[
            "mask_id"
        ]

        return self._insert(
            self._masks,
            key,
            mask,
        )

    def project_primitive(
        self,
        primitive: ConstructionPrimitive,
        *,
        fill: str = "none",
        stroke: str | None = None,
        stroke_width: float | None = None,
        opacity: float = 1.0,
    ) -> str:
        primitive_data = (
            primitive.normalized()
        )

        primitive_id = (
            primitive_data[
                "primitive_id"
            ]
        )

        existing_digest = (
            self._primitive_digests.get(
                primitive_id
            )
        )

        if (
            existing_digest is not None
            and existing_digest
            != primitive_data[
                "digest"
            ]
        ):
            raise BlotSvgError(
                "primitive projection identity "
                f"conflict: {primitive_id}"
            )

        path = path_from_primitive(
            primitive,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
        )

        path_id = self.add_path(
            path
        )

        self._primitive_digests[
            primitive_id
        ] = primitive_data[
            "digest"
        ]

        return path_id

    def document(
        self,
        *,
        metadata: Mapping[
            str,
            Any
        ] | None = None,
    ) -> SvgDocument:
        contract_data = (
            self.contract.normalized()
        )

        projection_metadata = {
            "schema":
                schema,

            "name":
                name,

            "profile":
                self.profile,

            "source_construction_digest":
                contract_data[
                    "construction_digest"
                ],

            "execution_contract_digest":
                contract_data[
                    "digest"
                ],

            "candidate_id":
                contract_data[
                    "candidate_id"
                ],

            "projected_primitives":
                [
                    {
                        "primitive_id":
                            primitive_id,

                        "primitive_digest":
                            self._primitive_digests[
                                primitive_id
                            ],
                    }
                    for primitive_id
                    in sorted(
                        self._primitive_digests
                    )
                ],

            "projection_is_authority":
                False,

            "svg_is_derived":
                True,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        if metadata:
            projection_metadata[
                "projection_metadata"
            ] = dict(metadata)

        return SvgDocument(
            width=self.width,
            height=self.height,
            view_box=tuple(
                _finite(
                    value,
                    "view_box",
                )
                for value
                in self.view_box
            ),
            paths=tuple(
                self._paths[key]
                for key in sorted(
                    self._paths
                )
            ),
            groups=tuple(
                self._groups[key]
                for key in sorted(
                    self._groups
                )
            ),
            linear_gradients=tuple(
                self._linear_gradients[key]
                for key in sorted(
                    self._linear_gradients
                )
            ),
            radial_gradients=tuple(
                self._radial_gradients[key]
                for key in sorted(
                    self._radial_gradients
                )
            ),
            clip_paths=tuple(
                self._clip_paths[key]
                for key in sorted(
                    self._clip_paths
                )
            ),
            masks=tuple(
                self._masks[key]
                for key in sorted(
                    self._masks
                )
            ),
            metadata=projection_metadata,
        )

    def render(
        self,
        *,
        metadata: Mapping[
            str,
            Any
        ] | None = None,
    ) -> str:
        return self.document(
            metadata=metadata
        ).render()

    def manifest(self) -> dict[str, Any]:
        document = self.document()
        normalized = document.normalized()

        body = {
            "schema":
                f"{schema}.manifest",

            "name":
                name,

            "profile":
                self.profile,

            "document_digest":
                normalized[
                    "digest"
                ],

            "execution_contract_digest":
                self.contract
                .normalized()[
                    "digest"
                ],

            "path_count":
                len(self._paths),

            "group_count":
                len(self._groups),

            "linear_gradient_count":
                len(
                    self._linear_gradients
                ),

            "radial_gradient_count":
                len(
                    self._radial_gradients
                ),

            "clip_path_count":
                len(self._clip_paths),

            "mask_count":
                len(self._masks),

            "projected_primitive_count":
                len(
                    self._primitive_digests
                ),

            "projection_is_authority":
                False,

            "svg_is_derived":
                True,

            "deterministic":
                True,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        body["digest"] = _digest(body)

        return body


def selftest() -> dict[str, Any]:
    primitive = ConstructionPrimitive(
        primitive_id="upper-ribbon",
        kind="closed-cubic-bezier",
        parameters={
            "d":
                (
                    "M 10 50 "
                    "C 25 10 75 10 90 50 "
                    "C 75 90 25 90 10 50 Z"
                ),

            "fill_rule":
                "nonzero",
        },
        confidence=1.0,
        state="authored",
        provenance=(
            "selftest",
        ),
    )

    from runtime.translucent.blot_reconstruction import (
        ExecutionStep,
    )

    step = ExecutionStep(
        step_id="construct-upper",
        stage_id=(
            "r3-04-primary-bezier-silhouettes"
        ),
        operation=(
            "construct-primary-bezier"
        ),
        primitive_ids=(
            "upper-ribbon",
        ),
    )

    contract = ExecutionContract(
        candidate_id="semantic-ribbons",
        construction_digest=(
            "selftest-construction"
        ),
        steps=(
            step,
        ),
        topology_resolved=True,
        geometry_resolved=True,
        negative_space_resolved=True,
        booleans_resolved=True,
        materials_resolved=True,
        lighting_resolved=True,
        masks_resolved=True,
        gradients_resolved=True,
        ambiguous=(),
        blocking_ambiguities=0,
        predicted_counts={
            "paths": 1,
            "anchors": 6,
            "gradients": 1,
            "masks": 0,
            "clips": 0,
            "filters": 0,
        },
        execution_ready=True,
    )

    gradient = SvgLinearGradient(
        gradient_id="material-gold",
        x1=0,
        y1=0,
        x2=100,
        y2=100,
        stops=(
            SvgStop(
                0.0,
                "#ff9f1c",
            ),
            SvgStop(
                0.5,
                "#ffd166",
            ),
            SvgStop(
                1.0,
                "#ff7a00",
            ),
        ),
    )

    builder_a = ProjectionBuilder(
        contract,
        width=100,
        height=100,
    )

    builder_a.add_linear_gradient(
        gradient
    )

    builder_a.project_primitive(
        primitive,
        fill="url(#material-gold)",
    )

    svg_a = builder_a.render()
    svg_b = builder_a.render()

    builder_b = ProjectionBuilder(
        contract,
        width=100,
        height=100,
    )

    builder_b.add_linear_gradient(
        gradient
    )

    builder_b.project_primitive(
        primitive,
        fill="url(#material-gold)",
    )

    manifest_a = (
        builder_a.manifest()
    )

    manifest_b = (
        builder_b.manifest()
    )

    checks = {
        "name_exact":
            name == "blot.",

        "authority_none":
            authority_effect
            == "none",

        "mutation_none":
            mutation_effect
            == "none",

        "projection_only":
            projection_only is True,

        "svg_derived":
            manifest_a[
                "svg_is_derived"
            ]
            is True,

        "projection_not_authority":
            manifest_a[
                "projection_is_authority"
            ]
            is False,

        "single_path":
            manifest_a[
                "path_count"
            ]
            == 1,

        "single_gradient":
            manifest_a[
                "linear_gradient_count"
            ]
            == 1,

        "primitive_bound":
            manifest_a[
                "projected_primitive_count"
            ]
            == 1,

        "contains_svg":
            "<svg"
            in svg_a,

        "contains_path":
            "<path"
            in svg_a,

        "contains_gradient":
            "linearGradient"
            in svg_a,

        "contains_metadata":
            "<metadata"
            in svg_a,

        "no_embedded_raster":
            "<image"
            not in svg_a,

        "deterministic_render":
            svg_a == svg_b,

        "deterministic_projection":
            manifest_a
            == manifest_b,

        "contract_bound":
            manifest_a[
                "execution_contract_digest"
            ]
            == contract.normalized()[
                "digest"
            ],
    }

    result = {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "manifest":
            manifest_a,

        "svg_digest":
            _digest(svg_a),

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,
    }

    result["digest"] = _digest(result)

    return result


__all__ = [
    "BlotSvgError",
    "ProjectionBuilder",
    "SvgClipPath",
    "SvgDocument",
    "SvgGroup",
    "SvgLinearGradient",
    "SvgMask",
    "SvgPath",
    "SvgRadialGradient",
    "SvgStop",
    "authority_effect",
    "max_clip_elements",
    "max_filter_elements",
    "max_gradient_stops",
    "max_mask_elements",
    "max_path_commands",
    "max_svg_elements",
    "mutation_effect",
    "name",
    "path_from_primitive",
    "projection_only",
    "schema",
    "selftest",
    "svg_ns",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
