#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from runtime.translucent.blot_reconstruction import (
    BlotReconstructionError,
    ExecutionContract,
)


name = "blot."
schema = "savant.translucent.svg.blot.reconstruction.v1"
authority_effect = "none"
projection_only = True

max_svg_elements = 16384
max_path_commands = 32768
max_gradient_stops = 64
max_mask_elements = 256
max_clip_elements = 256
max_filter_elements = 128

_number_pattern = re.compile(
    r"^-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)

_path_token_pattern = re.compile(
    r"""
    [MmZzLlHhVvCcSsQqTtAa]
    |
    -?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?
    """,
    re.VERBOSE,
)

_allowed_path_commands = frozenset(
    "MmZzLlHhVvCcSsQqTtAa"
)

_allowed_linecaps = frozenset(
    {
        "butt",
        "round",
        "square",
    }
)

_allowed_linejoins = frozenset(
    {
        "miter",
        "round",
        "bevel",
    }
)

_allowed_fill_rules = frozenset(
    {
        "nonzero",
        "evenodd",
    }
)

_allowed_spread_methods = frozenset(
    {
        "pad",
        "reflect",
        "repeat",
    }
)


class BlotSvgError(BlotReconstructionError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _text(value: Any, label: str) -> str:
    result = str(value).strip()

    if not result:
        raise BlotSvgError(
            f"{label} is required"
        )

    return result


def _id(value: Any, label: str) -> str:
    result = _text(
        value,
        label,
    )

    if not re.fullmatch(
        r"[a-zA-Z_][a-zA-Z0-9_.:-]*",
        result,
    ):
        raise BlotSvgError(
            f"invalid svg id for {label}: {result}"
        )

    return result


def _finite(value: Any, label: str) -> float:
    try:
        result = float(
            value
        )
    except (TypeError, ValueError) as exc:
        raise BlotSvgError(
            f"{label} must be numeric"
        ) from exc

    if not math.isfinite(
        result
    ):
        raise BlotSvgError(
            f"{label} must be finite"
        )

    return result


def _number(value: Any) -> str:
    result = _finite(
        value,
        "number",
    )

    if result == 0:
        return "0"

    rendered = format(
        result,
        ".12g",
    )

    if rendered == "-0":
        return "0"

    return rendered


def _escape(value: Any) -> str:
    return html.escape(
        str(value),
        quote=True,
    )


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if str(value).strip()
        )
    )


def _color(value: Any) -> str:
    result = _text(
        value,
        "color",
    )

    if re.fullmatch(
        r"#[0-9a-fA-F]{3,8}",
        result,
    ):
        return result.lower()

    if re.fullmatch(
        r"(?:rgb|rgba|hsl|hsla)\([^<>]*\)",
        result,
    ):
        return result

    if re.fullmatch(
        r"[a-zA-Z]+",
        result,
    ):
        return result.lower()

    if result == "none":
        return result

    raise BlotSvgError(
        f"invalid color: {result}"
    )


def _opacity(value: Any) -> str:
    result = _finite(
        value,
        "opacity",
    )

    if not 0.0 <= result <= 1.0:
        raise BlotSvgError(
            "opacity must be between zero and one"
        )

    return _number(
        result
    )


def _path_data(value: Any) -> str:
    source = _text(
        value,
        "path data",
    )

    tokens = _path_token_pattern.findall(
        source
    )

    compact_source = re.sub(
        r"[\s,]+",
        "",
        source,
    )

    compact_tokens = "".join(
        tokens
    )

    if compact_source != compact_tokens:
        raise BlotSvgError(
            "path contains unsupported syntax"
        )

    command_count = sum(
        1
        for token in tokens
        if token in _allowed_path_commands
    )

    if command_count == 0:
        raise BlotSvgError(
            "path contains no commands"
        )

    if command_count > max_path_commands:
        raise BlotSvgError(
            "path command limit exceeded"
        )

    return " ".join(
        tokens
    )


def _transform(
    value: Any,
) -> str | None:
    if value is None:
        return None

    source = _text(
        value,
        "transform",
    )

    allowed = re.compile(
        r"""
        ^\s*
        (?:
            (?:
                matrix|
                translate|
                scale|
                rotate|
                skewX|
                skewY
            )
            \(
                [0-9eE+\-.,\s]+
            \)
            \s*
        )+
        $
        """,
        re.VERBOSE,
    )

    if not allowed.fullmatch(
        source
    ):
        raise BlotSvgError(
            "unsupported transform syntax"
        )

    return source


def _paint_reference(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = str(
        value
    ).strip()

    if not value:
        return None

    if value.startswith(
        "url(#"
    ) and value.endswith(
        ")"
    ):
        referenced = value[
            5:-1
        ]

        return (
            "url(#"
            + _id(
                referenced,
                "paint reference",
            )
            + ")"
        )

    return _color(
        value
    )


@dataclass(frozen=True, slots=True)
class SvgStop:
    offset: float
    color: str
    opacity: float = 1.0

    def render(self) -> str:
        offset = _finite(
            self.offset,
            "gradient stop offset",
        )

        if not 0.0 <= offset <= 1.0:
            raise BlotSvgError(
                "gradient stop offset must be between zero and one"
            )

        return (
            '<stop offset="'
            + _number(
                offset
            )
            + '" stop-color="'
            + _escape(
                _color(
                    self.color
                )
            )
            + '" stop-opacity="'
            + _opacity(
                self.opacity
            )
            + '"/>'
        )


@dataclass(frozen=True, slots=True)
class SvgLinearGradient:
    gradient_id: str
    stops: tuple[SvgStop, ...]
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 1.0
    y2: float = 0.0
    gradient_units: str = "objectBoundingBox"
    spread_method: str = "pad"
    transform: str | None = None

    def render(self) -> str:
        gradient_id = _id(
            self.gradient_id,
            "gradient_id",
        )

        if not 2 <= len(
            self.stops
        ) <= max_gradient_stops:
            raise BlotSvgError(
                "linear gradient stop count outside limits"
            )

        if self.gradient_units not in {
            "objectBoundingBox",
            "userSpaceOnUse",
        }:
            raise BlotSvgError(
                "invalid gradient units"
            )

        if self.spread_method not in _allowed_spread_methods:
            raise BlotSvgError(
                "invalid gradient spread method"
            )

        attributes = [
            f'id="{_escape(gradient_id)}"',
            f'x1="{_number(self.x1)}"',
            f'y1="{_number(self.y1)}"',
            f'x2="{_number(self.x2)}"',
            f'y2="{_number(self.y2)}"',
            f'gradientUnits="{self.gradient_units}"',
            f'spreadMethod="{self.spread_method}"',
        ]

        transform = _transform(
            self.transform
        )

        if transform is not None:
            attributes.append(
                'gradientTransform="'
                + _escape(
                    transform
                )
                + '"'
            )

        return (
            "<linearGradient "
            + " ".join(
                attributes
            )
            + ">"
            + "".join(
                stop.render()
                for stop in self.stops
            )
            + "</linearGradient>"
        )


@dataclass(frozen=True, slots=True)
class SvgRadialGradient:
    gradient_id: str
    stops: tuple[SvgStop, ...]
    cx: float = 0.5
    cy: float = 0.5
    r: float = 0.5
    fx: float | None = None
    fy: float | None = None
    gradient_units: str = "objectBoundingBox"
    spread_method: str = "pad"
    transform: str | None = None

    def render(self) -> str:
        gradient_id = _id(
            self.gradient_id,
            "gradient_id",
        )

        if not 2 <= len(
            self.stops
        ) <= max_gradient_stops:
            raise BlotSvgError(
                "radial gradient stop count outside limits"
            )

        if self.gradient_units not in {
            "objectBoundingBox",
            "userSpaceOnUse",
        }:
            raise BlotSvgError(
                "invalid gradient units"
            )

        if self.spread_method not in _allowed_spread_methods:
            raise BlotSvgError(
                "invalid gradient spread method"
            )

        radius = _finite(
            self.r,
            "radial gradient radius",
        )

        if radius <= 0:
            raise BlotSvgError(
                "radial gradient radius must be positive"
            )

        attributes = [
            f'id="{_escape(gradient_id)}"',
            f'cx="{_number(self.cx)}"',
            f'cy="{_number(self.cy)}"',
            f'r="{_number(radius)}"',
            f'gradientUnits="{self.gradient_units}"',
            f'spreadMethod="{self.spread_method}"',
        ]

        if self.fx is not None:
            attributes.append(
                f'fx="{_number(self.fx)}"'
            )

        if self.fy is not None:
            attributes.append(
                f'fy="{_number(self.fy)}"'
            )

        transform = _transform(
            self.transform
        )

        if transform is not None:
            attributes.append(
                'gradientTransform="'
                + _escape(
                    transform
                )
                + '"'
            )

        return (
            "<radialGradient "
            + " ".join(
                attributes
            )
            + ">"
            + "".join(
                stop.render()
                for stop in self.stops
            )
            + "</radialGradient>"
        )


@dataclass(frozen=True, slots=True)
class SvgPath:
    element_id: str
    d: str
    fill: str | None = None
    stroke: str | None = None
    stroke_width: float | None = None
    fill_rule: str = "nonzero"
    opacity: float = 1.0
    transform: str | None = None
    clip_id: str | None = None
    mask_id: str | None = None
    linecap: str | None = None
    linejoin: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def render(self) -> str:
        element_id = _id(
            self.element_id,
            "element_id",
        )

        if self.fill_rule not in _allowed_fill_rules:
            raise BlotSvgError(
                "invalid fill rule"
            )

        attributes = [
            f'id="{_escape(element_id)}"',
            f'd="{_escape(_path_data(self.d))}"',
            f'fill-rule="{self.fill_rule}"',
            f'opacity="{_opacity(self.opacity)}"',
        ]

        fill = _paint_reference(
            self.fill
        )

        stroke = _paint_reference(
            self.stroke
        )

        attributes.append(
            'fill="'
            + _escape(
                fill
                if fill is not None
                else "none"
            )
            + '"'
        )

        if stroke is not None:
            attributes.append(
                f'stroke="{_escape(stroke)}"'
            )

        if self.stroke_width is not None:
            width = _finite(
                self.stroke_width,
                "stroke_width",
            )

            if width < 0:
                raise BlotSvgError(
                    "stroke width cannot be negative"
                )

            attributes.append(
                f'stroke-width="{_number(width)}"'
            )

        if self.linecap is not None:
            if self.linecap not in _allowed_linecaps:
                raise BlotSvgError(
                    "invalid stroke linecap"
                )

            attributes.append(
                f'stroke-linecap="{self.linecap}"'
            )

        if self.linejoin is not None:
            if self.linejoin not in _allowed_linejoins:
                raise BlotSvgError(
                    "invalid stroke linejoin"
                )

            attributes.append(
                f'stroke-linejoin="{self.linejoin}"'
            )

        transform = _transform(
            self.transform
        )

        if transform is not None:
            attributes.append(
                'transform="'
                + _escape(
                    transform
                )
                + '"'
            )

        if self.clip_id is not None:
            attributes.append(
                'clip-path="url(#'
                + _escape(
                    _id(
                        self.clip_id,
                        "clip_id",
                    )
                )
                + ')"'
            )

        if self.mask_id is not None:
            attributes.append(
                'mask="url(#'
                + _escape(
                    _id(
                        self.mask_id,
                        "mask_id",
                    )
                )
                + ')"'
            )

        metadata = dict(
            self.metadata
        )

        if metadata:
            attributes.append(
                'data-savant="'
                + _escape(
                    _canonical(
                        metadata
                    )
                )
                + '"'
            )

        return (
            "<path "
            + " ".join(
                attributes
            )
            + "/>"
        )


@dataclass(frozen=True, slots=True)
class SvgClipPath:
    clip_id: str
    paths: tuple[SvgPath, ...]

    def render(self) -> str:
        if len(
            self.paths
        ) > max_clip_elements:
            raise BlotSvgError(
                "clip path element limit exceeded"
            )

        return (
            '<clipPath id="'
            + _escape(
                _id(
                    self.clip_id,
                    "clip_id",
                )
            )
            + '">'
            + "".join(
                path.render()
                for path in self.paths
            )
            + "</clipPath>"
        )


@dataclass(frozen=True, slots=True)
class SvgMask:
    mask_id: str
    paths: tuple[SvgPath, ...]
    mask_units: str = "objectBoundingBox"

    def render(self) -> str:
        if len(
            self.paths
        ) > max_mask_elements:
            raise BlotSvgError(
                "mask element limit exceeded"
            )

        if self.mask_units not in {
            "objectBoundingBox",
            "userSpaceOnUse",
        }:
            raise BlotSvgError(
                "invalid mask units"
            )

        return (
            '<mask id="'
            + _escape(
                _id(
                    self.mask_id,
                    "mask_id",
                )
            )
            + '" maskUnits="'
            + self.mask_units
            + '">'
            + "".join(
                path.render()
                for path in self.paths
            )
            + "</mask>"
        )


@dataclass(frozen=True, slots=True)
class SvgGroup:
    group_id: str
    children: tuple[Any, ...]
    transform: str | None = None
    opacity: float = 1.0
    clip_id: str | None = None
    mask_id: str | None = None
    role: str | None = None

    def render(self) -> str:
        attributes = [
            'id="'
            + _escape(
                _id(
                    self.group_id,
                    "group_id",
                )
            )
            + '"',

            'opacity="'
            + _opacity(
                self.opacity
            )
            + '"',
        ]

        transform = _transform(
            self.transform
        )

        if transform is not None:
            attributes.append(
                'transform="'
                + _escape(
                    transform
                )
                + '"'
            )

        if self.clip_id is not None:
            attributes.append(
                'clip-path="url(#'
                + _escape(
                    _id(
                        self.clip_id,
                        "clip_id",
                    )
                )
                + ')"'
            )

        if self.mask_id is not None:
            attributes.append(
                'mask="url(#'
                + _escape(
                    _id(
                        self.mask_id,
                        "mask_id",
                    )
                )
                + ')"'
            )

        if self.role is not None:
            attributes.append(
                'data-role="'
                + _escape(
                    _text(
                        self.role,
                        "role",
                    )
                )
                + '"'
            )

        return (
            "<g "
            + " ".join(
                attributes
            )
            + ">"
            + "".join(
                child.render()
                for child in self.children
            )
            + "</g>"
        )


@dataclass(frozen=True, slots=True)
class SvgDocument:
    width: float
    height: float
    view_box: tuple[float, float, float, float]
    children: tuple[Any, ...]
    gradients: tuple[Any, ...] = ()
    clips: tuple[SvgClipPath, ...] = ()
    masks: tuple[SvgMask, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def render(self) -> str:
        width = _finite(
            self.width,
            "width",
        )

        height = _finite(
            self.height,
            "height",
        )

        if width <= 0 or height <= 0:
            raise BlotSvgError(
                "svg dimensions must be positive"
            )

        if len(
            self.view_box
        ) != 4:
            raise BlotSvgError(
                "view_box must contain four values"
            )

        view_box = tuple(
            _finite(
                value,
                "view_box",
            )
            for value in self.view_box
        )

        if (
            view_box[2] <= 0
            or view_box[3] <= 0
        ):
            raise BlotSvgError(
                "view_box dimensions must be positive"
            )

        total_elements = (
            len(
                self.children
            )
            + len(
                self.gradients
            )
            + len(
                self.clips
            )
            + len(
                self.masks
            )
        )

        if total_elements > max_svg_elements:
            raise BlotSvgError(
                "svg element limit exceeded"
            )

        definition_ids: set[str] = set()

        for definition in (
            tuple(
                self.gradients
            )
            + tuple(
                self.clips
            )
            + tuple(
                self.masks
            )
        ):
            if isinstance(
                definition,
                (
                    SvgLinearGradient,
                    SvgRadialGradient,
                ),
            ):
                identifier = definition.gradient_id
            elif isinstance(
                definition,
                SvgClipPath,
            ):
                identifier = definition.clip_id
            elif isinstance(
                definition,
                SvgMask,
            ):
                identifier = definition.mask_id
            else:
                raise BlotSvgError(
                    "unsupported svg definition"
                )

            identifier = _id(
                identifier,
                "definition id",
            )

            if identifier in definition_ids:
                raise BlotSvgError(
                    "duplicate svg definition id: "
                    f"{identifier}"
                )

            definition_ids.add(
                identifier
            )

        metadata = {
            "schema":
                schema,

            "authority_effect":
                authority_effect,

            "projection_only":
                projection_only,

            **dict(
                self.metadata
            ),
        }

        defs = "".join(
            definition.render()
            for definition in (
                tuple(
                    self.gradients
                )
                + tuple(
                    self.clips
                )
                + tuple(
                    self.masks
                )
            )
        )

        body = "".join(
            child.render()
            for child in self.children
        )

        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'width="'
            + _number(
                width
            )
            + '" height="'
            + _number(
                height
            )
            + '" viewBox="'
            + " ".join(
                _number(
                    value
                )
                for value in view_box
            )
            + '" role="img">'
            '<metadata id="savant-metadata">'
            + _escape(
                _canonical(
                    metadata
                )
            )
            + "</metadata>"
            + (
                "<defs>"
                + defs
                + "</defs>"
                if defs
                else ""
            )
            + body
            + "</svg>"
        )

    def digest(self) -> str:
        return hashlib.sha256(
            self.render().encode(
                "utf-8"
            )
        ).hexdigest()


class ProjectionBuilder:
    def __init__(
        self,
        contract: ExecutionContract,
        *,
        width: float,
        height: float,
        view_box: Sequence[float] | None = None,
    ) -> None:
        normalized = contract.normalized()

        if not normalized[
            "execution_ready"
        ]:
            raise BlotSvgError(
                "execution contract is not ready"
            )

        self.contract = contract
        self.contract_data = normalized

        self.width = _finite(
            width,
            "width",
        )

        self.height = _finite(
            height,
            "height",
        )

        if self.width <= 0 or self.height <= 0:
            raise BlotSvgError(
                "projection dimensions must be positive"
            )

        if view_box is None:
            self.view_box = (
                0.0,
                0.0,
                self.width,
                self.height,
            )
        else:
            if len(
                view_box
            ) != 4:
                raise BlotSvgError(
                    "view_box must contain four values"
                )

            self.view_box = tuple(
                _finite(
                    value,
                    "view_box",
                )
                for value in view_box
            )

        self._gradients: dict[
            str,
            Any,
        ] = {}

        self._clips: dict[
            str,
            SvgClipPath,
        ] = {}

        self._masks: dict[
            str,
            SvgMask,
        ] = {}

        self._layers: dict[
            str,
            list[Any],
        ] = {
            "geometry": [],
            "materials": [],
            "bevels": [],
            "reflections": [],
            "highlights": [],
            "shadows": [],
            "effects": [],
        }

        self._primitive_outputs: dict[
            str,
            tuple[str, ...],
        ] = {}

        self._step_outputs: dict[
            str,
            tuple[str, ...],
        ] = {}

    def add_gradient(
        self,
        gradient: Any,
    ) -> None:
        if isinstance(
            gradient,
            (
                SvgLinearGradient,
                SvgRadialGradient,
            ),
        ):
            gradient_id = gradient.gradient_id
        else:
            raise BlotSvgError(
                "unsupported gradient type"
            )

        gradient_id = _id(
            gradient_id,
            "gradient_id",
        )

        existing = self._gradients.get(
            gradient_id
        )

        if (
            existing is not None
            and existing.render()
            != gradient.render()
        ):
            raise BlotSvgError(
                "conflicting gradient id: "
                f"{gradient_id}"
            )

        self._gradients[
            gradient_id
        ] = gradient

    def add_clip(
        self,
        clip: SvgClipPath,
    ) -> None:
        clip_id = _id(
            clip.clip_id,
            "clip_id",
        )

        existing = self._clips.get(
            clip_id
        )

        if (
            existing is not None
            and existing.render()
            != clip.render()
        ):
            raise BlotSvgError(
                "conflicting clip id: "
                f"{clip_id}"
            )

        self._clips[
            clip_id
        ] = clip

    def add_mask(
        self,
        mask: SvgMask,
    ) -> None:
        mask_id = _id(
            mask.mask_id,
            "mask_id",
        )

        existing = self._masks.get(
            mask_id
        )

        if (
            existing is not None
            and existing.render()
            != mask.render()
        ):
            raise BlotSvgError(
                "conflicting mask id: "
                f"{mask_id}"
            )

        self._masks[
            mask_id
        ] = mask

    def add(
        self,
        layer: str,
        element: Any,
        *,
        primitive_ids: Iterable[str] = (),
        step_id: str | None = None,
    ) -> None:
        layer = _text(
            layer,
            "layer",
        )

        if layer not in self._layers:
            raise BlotSvgError(
                f"unknown projection layer: {layer}"
            )

        if not hasattr(
            element,
            "render",
        ):
            raise BlotSvgError(
                "projection element is not renderable"
            )

        self._layers[
            layer
        ].append(
            element
        )

        element_id = getattr(
            element,
            "element_id",
            getattr(
                element,
                "group_id",
                None,
            ),
        )

        if element_id is not None:
            element_id = str(
                element_id
            )

            for primitive_id in _unique(
                primitive_ids
            ):
                previous = self._primitive_outputs.get(
                    primitive_id,
                    (),
                )

                self._primitive_outputs[
                    primitive_id
                ] = _unique(
                    (
                        *previous,
                        element_id,
                    )
                )

            if step_id is not None:
                step_id = _text(
                    step_id,
                    "step_id",
                )

                previous = self._step_outputs.get(
                    step_id,
                    (),
                )

                self._step_outputs[
                    step_id
                ] = _unique(
                    (
                        *previous,
                        element_id,
                    )
                )

    def document(self) -> SvgDocument:
        groups: list[SvgGroup] = []

        for layer_name in (
            "shadows",
            "geometry",
            "materials",
            "bevels",
            "reflections",
            "highlights",
            "effects",
        ):
            children = tuple(
                self._layers[
                    layer_name
                ]
            )

            if not children:
                continue

            groups.append(
                SvgGroup(
                    group_id=(
                        "blot-"
                        + layer_name
                    ),
                    children=children,
                    role=layer_name,
                )
            )

        metadata = {
            "name":
                name,

            "contract_id":
                self.contract_data[
                    "contract_id"
                ],

            "contract_digest":
                self.contract_data[
                    "digest"
                ],

            "source_digest":
                self.contract_data[
                    "source_digest"
                ],

            "construction_digest":
                self.contract_data[
                    "construction_digest"
                ],

            "candidate_id":
                self.contract_data[
                    "candidate_id"
                ],

            "primitive_outputs":
                {
                    key:
                        list(
                            self._primitive_outputs[
                                key
                            ]
                        )
                    for key
                    in sorted(
                        self._primitive_outputs
                    )
                },

            "step_outputs":
                {
                    key:
                        list(
                            self._step_outputs[
                                key
                            ]
                        )
                    for key
                    in sorted(
                        self._step_outputs
                    )
                },

            "lineage":
                self.contract_data[
                    "lineage"
                ],

            "provenance":
                self.contract_data[
                    "provenance"
                ],

            "geometry_owns_shape":
                True,

            "materials_decorate_geometry":
                True,

            "effects_are_non_authoritative":
                True,
        }

        return SvgDocument(
            width=self.width,
            height=self.height,
            view_box=self.view_box,
            children=tuple(
                groups
            ),
            gradients=tuple(
                self._gradients[
                    key
                ]
                for key
                in sorted(
                    self._gradients
                )
            ),
            clips=tuple(
                self._clips[
                    key
                ]
                for key
                in sorted(
                    self._clips
                )
            ),
            masks=tuple(
                self._masks[
                    key
                ]
                for key
                in sorted(
                    self._masks
                )
            ),
            metadata=metadata,
        )

    def projection_receipt(
        self,
    ) -> dict[str, Any]:
        document = self.document()

        result = {
            "schema":
                f"{schema}.projection-receipt",

            "contract_id":
                self.contract_data[
                    "contract_id"
                ],

            "contract_digest":
                self.contract_data[
                    "digest"
                ],

            "svg_digest":
                document.digest(),

            "gradient_count":
                len(
                    self._gradients
                ),

            "clip_count":
                len(
                    self._clips
                ),

            "mask_count":
                len(
                    self._masks
                ),

            "layer_counts":
                {
                    key:
                        len(
                            self._layers[
                                key
                            ]
                        )
                    for key
                    in sorted(
                        self._layers
                    )
                },

            "primitive_outputs":
                {
                    key:
                        list(
                            self._primitive_outputs[
                                key
                            ]
                        )
                    for key
                    in sorted(
                        self._primitive_outputs
                    )
                },

            "step_outputs":
                {
                    key:
                        list(
                            self._step_outputs[
                                key
                            ]
                        )
                    for key
                    in sorted(
                        self._step_outputs
                    )
                },

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result


def path_from_primitive(
    primitive: Mapping[str, Any],
    *,
    element_id: str | None = None,
    fill: str | None = None,
    stroke: str | None = None,
    stroke_width: float | None = None,
    opacity: float = 1.0,
    transform: str | None = None,
    clip_id: str | None = None,
    mask_id: str | None = None,
) -> SvgPath:
    primitive_id = _text(
        primitive.get(
            "primitive_id"
        ),
        "primitive_id",
    )

    kind = _text(
        primitive.get(
            "kind"
        ),
        "kind",
    )

    parameters = primitive.get(
        "parameters"
    )

    if not isinstance(
        parameters,
        Mapping,
    ):
        raise BlotSvgError(
            "primitive parameters must be a mapping"
        )

    path_data = parameters.get(
        "d"
    )

    if path_data is None:
        path_data = parameters.get(
            "path"
        )

    if path_data is None:
        raise BlotSvgError(
            "primitive does not contain path geometry"
        )

    fill_rule = str(
        parameters.get(
            "fill_rule",
            "nonzero",
        )
    )

    return SvgPath(
        element_id=(
            element_id
            if element_id is not None
            else "primitive-"
            + re.sub(
                r"[^a-zA-Z0-9_.:-]+",
                "-",
                primitive_id,
            )
        ),
        d=str(
            path_data
        ),
        fill=(
            fill
            if fill is not None
            else parameters.get(
                "fill"
            )
        ),
        stroke=(
            stroke
            if stroke is not None
            else parameters.get(
                "stroke"
            )
        ),
        stroke_width=(
            stroke_width
            if stroke_width is not None
            else parameters.get(
                "stroke_width"
            )
        ),
        fill_rule=fill_rule,
        opacity=opacity,
        transform=(
            transform
            if transform is not None
            else parameters.get(
                "transform"
            )
        ),
        clip_id=clip_id,
        mask_id=mask_id,
        linecap=parameters.get(
            "linecap"
        ),
        linejoin=parameters.get(
            "linejoin"
        ),
        metadata={
            "primitive_id":
                primitive_id,

            "primitive_kind":
                kind,

            "evidence_ids":
                list(
                    primitive.get(
                        "evidence_ids",
                        (),
                    )
                ),

            "dependencies":
                list(
                    primitive.get(
                        "dependencies",
                        (),
                    )
                ),

            "relationships":
                list(
                    primitive.get(
                        "relationships",
                        (),
                    )
                ),

            "confidence":
                primitive.get(
                    "confidence"
                ),

            "provenance":
                list(
                    primitive.get(
                        "provenance",
                        (),
                    )
                ),

            "lineage":
                list(
                    primitive.get(
                        "lineage",
                        (),
                    )
                ),
        },
    )


def selftest() -> dict[str, Any]:
    from runtime.translucent.blot_reconstruction import (
        Candidate,
        ConstructionPrimitive,
        Evidence,
        ExecutionStep,
        ReconstructionPipeline,
    )

    pipeline = ReconstructionPipeline(
        source_digest="svg-source-test"
    )

    evidence_id = pipeline.add_evidence(
        Evidence(
            evidence_id="evidence-1",
            kind="silhouette",
            payload={
                "source": "selftest",
            },
            provenance=(
                "selftest",
            ),
        )
    )

    primitive_id = pipeline.substantiate(
        ConstructionPrimitive(
            primitive_id="ribbon",
            kind="cubic-bezier-shape",
            parameters={
                "d":
                    "M 10 50 "
                    "C 20 10 80 10 90 50 "
                    "C 80 90 20 90 10 50 Z",

                "fill_rule":
                    "nonzero",
            },
            evidence_ids=(
                evidence_id,
            ),
            provenance=(
                "selftest",
            ),
        )
    )

    candidate_id = pipeline.add_candidate(
        Candidate(
            candidate_id="candidate-1",
            strategy="semantic-bezier",
            primitive_ids=(
                primitive_id,
            ),
            predicted_cost={
                "paths": 1,
                "anchors": 4,
            },
            predicted_quality={
                "fidelity": 1.0,
                "structural": 1.0,
                "editability": 1.0,
            },
        )
    )

    contract = pipeline.compile_execution_contract(
        candidate_id,
        (
            ExecutionStep(
                step_id="step-1",
                stage_id="bezier-build",
                operation="construct-cubic-bezier",
                primitive_ids=(
                    primitive_id,
                ),
            ),
        ),
    )

    graph = pipeline.construction_graph()

    primitive = graph[
        "primitives"
    ][0]

    gradient = SvgLinearGradient(
        gradient_id="material-steel",
        x1=0,
        y1=0,
        x2=1,
        y2=1,
        stops=(
            SvgStop(
                0.0,
                "#202020",
            ),
            SvgStop(
                0.5,
                "#f2f2f2",
            ),
            SvgStop(
                1.0,
                "#303030",
            ),
        ),
    )

    path = path_from_primitive(
        primitive,
        fill="url(#material-steel)",
    )

    builder = ProjectionBuilder(
        contract,
        width=100,
        height=100,
    )

    builder.add_gradient(
        gradient
    )

    builder.add(
        "geometry",
        path,
        primitive_ids=(
            primitive_id,
        ),
        step_id="step-1",
    )

    document_a = builder.document()
    document_b = builder.document()

    svg_a = document_a.render()
    svg_b = document_b.render()

    receipt_a = builder.projection_receipt()
    receipt_b = builder.projection_receipt()

    checks = {
        "name_exact":
            name
            == "blot.",

        "authority_none":
            authority_effect
            == "none",

        "projection_only":
            projection_only
            is True,

        "svg_root":
            "<svg "
            in svg_a,

        "metadata":
            "savant-metadata"
            in svg_a,

        "gradient":
            "material-steel"
            in svg_a,

        "path":
            "primitive-ribbon"
            in svg_a,

        "geometry_layer":
            "blot-geometry"
            in svg_a,

        "source_lineage":
            "svg-source-test"
            in svg_a,

        "deterministic_svg":
            svg_a
            == svg_b,

        "deterministic_receipt":
            receipt_a
            == receipt_b,

        "digest_matches":
            receipt_a[
                "svg_digest"
            ]
            == document_a.digest(),
    }

    return {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "svg_digest":
            document_a.digest(),

        "receipt_digest":
            receipt_a[
                "digest"
            ],
    }


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
    "name",
    "path_from_primitive",
    "projection_only",
    "schema",
    "selftest",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
