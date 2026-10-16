#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from ..blot import SCHEMA as BLOT_SCHEMA
from .runtime import (
    SVG_NS,
    TL_NS,
    TranslucentSVGError,
    TranslucentSVGRuntime,
)


schema = "savant.translucent.svg.blot.v1"
authority_effect = "none"

MAX_SHARDS = 100_000
MAX_INSTANCES = 250_000
MAX_SEGUES = 250_000
MAX_POINTS = 250_000

_SUPPORTED_GEOMETRY = frozenset(
    {
        "circle",
        "ellipse",
        "rect",
        "polygon",
        "star",
        "superellipse",
        "superformula",
        "path",
    }
)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TranslucentSVGError(
            f"blot projection value is not canonical-json compatible: {exc}"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = _canonical_json(value).encode("utf-8")

    return hashlib.sha256(data).hexdigest()


def _finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TranslucentSVGError(
            f"blot {name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise TranslucentSVGError(
            f"blot {name} must be finite"
        )

    return number


def _positive(value: Any, name: str) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise TranslucentSVGError(
            f"blot {name} must be positive"
        )

    return number


def _integer(
    value: Any,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool):
        raise TranslucentSVGError(
            f"blot {name} must be an integer"
        )

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise TranslucentSVGError(
            f"blot {name} must be an integer"
        ) from exc

    if number < minimum or number > maximum:
        raise TranslucentSVGError(
            f"blot {name} outside resource bounds"
        )

    return number


def _token(value: Any, name: str) -> str:
    token = str(value or "").strip()

    if not token:
        raise TranslucentSVGError(
            f"blot {name} is required"
        )

    return token


def _num(value: float) -> str:
    number = _finite(value, "number")

    if number == 0:
        number = 0.0

    text = format(number, ".12g")

    if text == "-0":
        return "0"

    return text


def _mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TranslucentSVGError(
            f"blot {name} must be a mapping"
        )

    return value


def _sequence(
    value: Any,
    name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise TranslucentSVGError(
            f"blot {name} must be a list"
        )

    return value


def _paint_attributes(
    paint: Mapping[str, Any],
) -> dict[str, str]:
    result: dict[str, str] = {}

    fill = paint.get("fill")
    stroke = paint.get("stroke")

    if fill is not None:
        result["fill"] = str(fill)

    if stroke is not None:
        result["stroke"] = str(stroke)

    stroke_width = paint.get("stroke_width")

    if stroke_width is not None:
        result["stroke-width"] = _num(
            _finite(
                stroke_width,
                "paint.stroke_width",
            )
        )

    opacity = paint.get("opacity")

    if opacity is not None:
        number = _finite(
            opacity,
            "paint.opacity",
        )

        if number < 0 or number > 1:
            raise TranslucentSVGError(
                "blot paint.opacity must be between 0 and 1"
            )

        result["opacity"] = _num(number)

    fill_opacity = paint.get("fill_opacity")

    if fill_opacity is not None:
        number = _finite(
            fill_opacity,
            "paint.fill_opacity",
        )

        if number < 0 or number > 1:
            raise TranslucentSVGError(
                "blot paint.fill_opacity must be between 0 and 1"
            )

        result["fill-opacity"] = _num(number)

    stroke_opacity = paint.get("stroke_opacity")

    if stroke_opacity is not None:
        number = _finite(
            stroke_opacity,
            "paint.stroke_opacity",
        )

        if number < 0 or number > 1:
            raise TranslucentSVGError(
                "blot paint.stroke_opacity must be between 0 and 1"
            )

        result["stroke-opacity"] = _num(number)

    linecap = paint.get("linecap")

    if linecap is not None:
        value = str(linecap)

        if value not in {
            "butt",
            "round",
            "square",
        }:
            raise TranslucentSVGError(
                "blot paint.linecap is invalid"
            )

        result["stroke-linecap"] = value

    linejoin = paint.get("linejoin")

    if linejoin is not None:
        value = str(linejoin)

        if value not in {
            "arcs",
            "bevel",
            "miter",
            "miter-clip",
            "round",
        }:
            raise TranslucentSVGError(
                "blot paint.linejoin is invalid"
            )

        result["stroke-linejoin"] = value

    return result


def _transform(
    value: Mapping[str, Any],
) -> str:
    x = _finite(
        value.get("x", 0.0),
        "transform.x",
    )

    y = _finite(
        value.get("y", 0.0),
        "transform.y",
    )

    scale_x = _finite(
        value.get("scale_x", 1.0),
        "transform.scale_x",
    )

    scale_y = _finite(
        value.get("scale_y", 1.0),
        "transform.scale_y",
    )

    rotate = _finite(
        value.get("rotate", 0.0),
        "transform.rotate",
    )

    skew_x = _finite(
        value.get("skew_x", 0.0),
        "transform.skew_x",
    )

    skew_y = _finite(
        value.get("skew_y", 0.0),
        "transform.skew_y",
    )

    operations: list[str] = []

    if x != 0 or y != 0:
        operations.append(
            f"translate({_num(x)} {_num(y)})"
        )

    if rotate != 0:
        operations.append(
            f"rotate({_num(rotate)})"
        )

    if skew_x != 0:
        operations.append(
            f"skewX({_num(skew_x)})"
        )

    if skew_y != 0:
        operations.append(
            f"skewY({_num(skew_y)})"
        )

    if scale_x != 1 or scale_y != 1:
        operations.append(
            f"scale({_num(scale_x)} {_num(scale_y)})"
        )

    return " ".join(operations)


def _points(
    values: Any,
) -> str:
    points = _sequence(
        values,
        "geometry points",
    )

    if len(points) > MAX_POINTS:
        raise TranslucentSVGError(
            "blot geometry point limit exceeded"
        )

    normalized: list[str] = []

    for index, point in enumerate(points):
        if not isinstance(
            point,
            (list, tuple),
        ) or len(point) != 2:
            raise TranslucentSVGError(
                f"blot geometry point {index} must contain x and y"
            )

        x = _finite(
            point[0],
            f"point[{index}].x",
        )

        y = _finite(
            point[1],
            f"point[{index}].y",
        )

        normalized.append(
            f"{_num(x)},{_num(y)}"
        )

    return " ".join(normalized)


def _geometry_element(
    shard: Mapping[str, Any],
) -> ET.Element:
    kind = _token(
        shard.get("kind"),
        "shard kind",
    )

    if kind not in _SUPPORTED_GEOMETRY:
        raise TranslucentSVGError(
            f"unsupported blot geometry shard: {kind}"
        )

    shard_id = _token(
        shard.get("shard_id"),
        "shard_id",
    )

    parameters = _mapping(
        shard.get("parameters", {}),
        "shard parameters",
    )

    if kind == "circle":
        radius = _positive(
            parameters.get("radius"),
            "circle.radius",
        )

        return ET.Element(
            f"{{{SVG_NS}}}circle",
            {
                "id": shard_id,
                "cx": "0",
                "cy": "0",
                "r": _num(radius),
            },
        )

    if kind == "ellipse":
        rx = _positive(
            parameters.get("rx"),
            "ellipse.rx",
        )

        ry = _positive(
            parameters.get("ry"),
            "ellipse.ry",
        )

        return ET.Element(
            f"{{{SVG_NS}}}ellipse",
            {
                "id": shard_id,
                "cx": "0",
                "cy": "0",
                "rx": _num(rx),
                "ry": _num(ry),
            },
        )

    if kind == "rect":
        width = _positive(
            parameters.get("width"),
            "rect.width",
        )

        height = _positive(
            parameters.get("height"),
            "rect.height",
        )

        radius = _finite(
            parameters.get("radius", 0.0),
            "rect.radius",
        )

        if radius < 0:
            raise TranslucentSVGError(
                "blot rect.radius cannot be negative"
            )

        return ET.Element(
            f"{{{SVG_NS}}}rect",
            {
                "id": shard_id,
                "x": _num(-width / 2),
                "y": _num(-height / 2),
                "width": _num(width),
                "height": _num(height),
                "rx": _num(radius),
            },
        )

    if kind in {
        "polygon",
        "star",
        "superellipse",
        "superformula",
    }:
        points = parameters.get("points")

        if points is None:
            points = shard.get("points")

        if points is None:
            raise TranslucentSVGError(
                f"blot {kind} projection requires normalized points"
            )

        return ET.Element(
            f"{{{SVG_NS}}}polygon",
            {
                "id": shard_id,
                "points": _points(points),
            },
        )

    if kind == "path":
        path = _token(
            parameters.get("d"),
            "path.d",
        )

        return ET.Element(
            f"{{{SVG_NS}}}path",
            {
                "id": shard_id,
                "d": path,
            },
        )

    raise TranslucentSVGError(
        f"unsupported blot geometry shard: {kind}"
    )


def _projection_metadata(
    root: ET.Element,
    payload: Mapping[str, Any],
) -> None:
    metadata = ET.SubElement(
        root,
        f"{{{SVG_NS}}}metadata",
    )

    projection = ET.SubElement(
        metadata,
        f"{{{TL_NS}}}projection",
        {
            "schema": schema,
            "source-schema": str(
                payload.get("schema")
                or BLOT_SCHEMA
            ),
            "authority-effect":
                authority_effect,
            "projection-only":
                "true",
            "source-digest": str(
                payload.get("digest")
                or _digest(payload)
            ),
        },
    )

    ET.SubElement(
        projection,
        f"{{{TL_NS}}}term",
        {
            "token": "instance",
            "ref": "lex:core:instance",
        },
    )

    ET.SubElement(
        projection,
        f"{{{TL_NS}}}term",
        {
            "token": "projection",
            "ref": "lex:core:projection",
        },
    )

    ET.SubElement(
        projection,
        f"{{{TL_NS}}}term",
        {
            "token": "segue",
            "ref": "lex:core:segue",
        },
    )


def blot_renderer(
    kind: str,
    payload: Mapping[str, Any],
    context: Mapping[str, Any],
    runtime: TranslucentSVGRuntime,
) -> str:
    del context

    if kind not in {
        "blot",
        "geometry",
        "geometry-projection",
    }:
        raise TranslucentSVGError(
            f"blot renderer does not support projection kind: {kind}"
        )

    if not isinstance(payload, Mapping):
        raise TranslucentSVGError(
            "blot renderer payload must be a mapping"
        )

    source_schema = str(
        payload.get("schema")
        or ""
    )

    if source_schema and source_schema != BLOT_SCHEMA:
        raise TranslucentSVGError(
            f"unsupported blot manifest schema: {source_schema}"
        )

    if payload.get("authority_effect") not in {
        None,
        "none",
    }:
        raise TranslucentSVGError(
            "blot projection cannot carry authority effects"
        )

    if payload.get("authoritative") is True:
        raise TranslucentSVGError(
            "blot projection cannot be authoritative"
        )

    width = _positive(
        payload.get("width", 1024),
        "width",
    )

    height = _positive(
        payload.get("height", 1024),
        "height",
    )

    shards = _sequence(
        payload.get("shards", []),
        "shards",
    )

    instances = _sequence(
        payload.get("instances", []),
        "instances",
    )

    segues = _sequence(
        payload.get("segues", []),
        "segues",
    )

    if len(shards) > MAX_SHARDS:
        raise TranslucentSVGError(
            "blot shard limit exceeded"
        )

    if len(instances) > MAX_INSTANCES:
        raise TranslucentSVGError(
            "blot instance limit exceeded"
        )

    if len(segues) > MAX_SEGUES:
        raise TranslucentSVGError(
            "blot segue limit exceeded"
        )

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox":
                f"{_num(-width / 2)} "
                f"{_num(-height / 2)} "
                f"{_num(width)} "
                f"{_num(height)}",
            "width": _num(width),
            "height": _num(height),
            "role": "img",
            "aria-labelledby":
                "tl-blot-title tl-blot-desc",
        },
    )

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}title",
        {
            "id": "tl-blot-title",
        },
    ).text = "Translucent blot projection"

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}desc",
        {
            "id": "tl-blot-desc",
        },
    ).text = (
        "A deterministic, non-authoritative SVG projection "
        "of reusable Translucent geometry shards and instances."
    )

    _projection_metadata(
        root,
        payload,
    )

    defs = ET.SubElement(
        root,
        f"{{{SVG_NS}}}defs",
    )

    shard_ids: set[str] = set()

    for index, item in enumerate(shards):
        shard = _mapping(
            item,
            f"shards[{index}]",
        )

        shard_id = _token(
            shard.get("shard_id"),
            f"shards[{index}].shard_id",
        )

        if shard_id in shard_ids:
            raise TranslucentSVGError(
                f"duplicate blot shard id: {shard_id}"
            )

        shard_ids.add(shard_id)

        defs.append(
            _geometry_element(shard)
        )

    instance_ids: set[str] = set()

    for index, item in enumerate(instances):
        instance = _mapping(
            item,
            f"instances[{index}]",
        )

        instance_id = _token(
            instance.get("instance_id"),
            f"instances[{index}].instance_id",
        )

        if instance_id in instance_ids:
            raise TranslucentSVGError(
                f"duplicate blot instance id: {instance_id}"
            )

        instance_ids.add(instance_id)

        shard_id = _token(
            instance.get("shard_id"),
            f"instances[{index}].shard_id",
        )

        if shard_id not in shard_ids:
            raise TranslucentSVGError(
                f"unknown blot instance shard: {shard_id}"
            )

        transform = _mapping(
            instance.get("transform", {}),
            f"instances[{index}].transform",
        )

        paint = _mapping(
            instance.get("paint", {}),
            f"instances[{index}].paint",
        )

        attributes = {
            "id": instance_id,
            "href": f"#{shard_id}",
            **_paint_attributes(paint),
        }

        transform_value = _transform(
            transform
        )

        if transform_value:
            attributes["transform"] = (
                transform_value
            )

        ET.SubElement(
            root,
            f"{{{SVG_NS}}}use",
            attributes,
        )

    for index, item in enumerate(segues):
        segue = _mapping(
            item,
            f"segues[{index}]",
        )

        source = _token(
            segue.get("source"),
            f"segues[{index}].source",
        )

        target = _token(
            segue.get("target"),
            f"segues[{index}].target",
        )

        if source not in instance_ids:
            raise TranslucentSVGError(
                f"unknown blot segue source: {source}"
            )

        if target not in instance_ids:
            raise TranslucentSVGError(
                f"unknown blot segue target: {target}"
            )

        _token(
            segue.get("kind"),
            f"segues[{index}].kind",
        )

    rendered = ET.tostring(
        root,
        encoding="unicode",
        short_empty_elements=True,
    )

    runtime.parse(rendered)

    return rendered


def register_blot_renderer(
    runtime: TranslucentSVGRuntime,
    *,
    replace: bool = False,
) -> None:
    runtime.register_renderer(
        "blot",
        blot_renderer,
        replace=replace,
    )


def manifest() -> dict[str, Any]:
    body = {
        "schema": schema,
        "owner": "savant",
        "kind": "translucent-svg-blot-projection",
        "source_schema": BLOT_SCHEMA,
        "renderer": "blot",
        "authority_effect": authority_effect,
        "projection_only": True,
        "authoritative": False,
        "supported_geometry":
            sorted(_SUPPORTED_GEOMETRY),
        "limits": {
            "max_shards": MAX_SHARDS,
            "max_instances": MAX_INSTANCES,
            "max_segues": MAX_SEGUES,
            "max_points": MAX_POINTS,
        },
    }

    return {
        **body,
        "digest": _digest(body),
    }


def selftest(
    runtime: TranslucentSVGRuntime,
) -> dict[str, Any]:
    payload = {
        "schema": BLOT_SCHEMA,
        "name": "blot.",
        "authority_effect": "none",
        "projection_only": True,
        "authoritative": False,
        "width": 320.0,
        "height": 240.0,
        "shards": [
            {
                "kind": "circle",
                "parameters": {
                    "radius": 24.0,
                },
                "shard_id": "geometry-circle-test",
                "digest": "a" * 64,
            },
        ],
        "instances": [
            {
                "shard_id":
                    "geometry-circle-test",
                "instance_id":
                    "geometry-instance-a",
                "transform": {
                    "x": -32.0,
                    "y": 0.0,
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "rotate": 0.0,
                    "skew_x": 0.0,
                    "skew_y": 0.0,
                },
                "paint": {
                    "fill": "#d9b44a",
                    "stroke": "#11151a",
                    "stroke_width": 2.0,
                    "opacity": 1.0,
                },
            },
            {
                "shard_id":
                    "geometry-circle-test",
                "instance_id":
                    "geometry-instance-b",
                "transform": {
                    "x": 32.0,
                    "y": 0.0,
                    "scale_x": -1.0,
                    "scale_y": 1.0,
                    "rotate": 0.0,
                    "skew_x": 0.0,
                    "skew_y": 0.0,
                },
                "paint": {
                    "fill": "#d9b44a",
                    "stroke": "#11151a",
                    "stroke_width": 2.0,
                    "opacity": 1.0,
                },
            },
        ],
        "segues": [
            {
                "kind": "mirror",
                "source":
                    "geometry-instance-a",
                "target":
                    "geometry-instance-b",
                "parameters": {
                    "axis": "y",
                },
            },
        ],
    }

    payload["digest"] = _digest(payload)

    first = runtime.render(
        "blot",
        payload,
        renderer="blot",
    )

    second = runtime.render(
        "blot",
        payload,
        renderer="blot",
    )

    parsed = runtime.parse(first)

    uses = parsed.findall(
        f"{{{SVG_NS}}}use"
    )

    symbols = parsed.find(
        f"{{{SVG_NS}}}defs"
    )

    checks = {
        "schema_exact":
            schema
            == "savant.translucent.svg.blot.v1",
        "source_schema_exact":
            BLOT_SCHEMA
            == "savant.translucent.blot.v1",
        "authority_none":
            authority_effect == "none",
        "renderer_registered":
            "blot"
            in runtime.renderer_names(),
        "deterministic_render":
            first == second,
        "single_substance_definition":
            symbols is not None
            and len(list(symbols)) == 1,
        "instance_reuse":
            len(uses) == 2,
        "typed_segue_preserved":
            payload["segues"][0]["kind"]
            == "mirror",
        "projection_only":
            payload["projection_only"]
            is True,
        "non_authoritative":
            payload["authoritative"]
            is False,
        "valid_svg":
            parsed.tag
            == f"{{{SVG_NS}}}svg",
    }

    result = {
        "schema":
            "savant.translucent.svg.blot-selftest.v1",
        "ok":
            all(checks.values()),
        "checks":
            checks,
        "manifest_digest":
            manifest()["digest"],
        "render_digest":
            _digest(first),
        "authority_effect":
            authority_effect,
    }

    result["digest"] = _digest(result)

    return result


__all__ = [
    "authority_effect",
    "blot_renderer",
    "manifest",
    "register_blot_renderer",
    "schema",
    "selftest",
]
