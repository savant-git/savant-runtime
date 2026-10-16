#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from runtime.translucent.svg.runtime import (
    SVG_NS,
    TL_NS,
    TranslucentSVGError,
    TranslucentSVGRuntime,
)


schema = "savant.translucent.svg.blot.v1"
owner = "savant"
authority_effect = "none"

max_shards = 100_000
max_instances = 250_000
max_segues = 250_000
max_points = 250_000

supported_geometry = frozenset(
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


def _canonical(value: Any) -> str:
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
            f"blot projection is not canonical-json compatible: {exc}"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _mapping(
    value: Any,
    field: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TranslucentSVGError(
            f"{field} must be a mapping"
        )

    return value


def _list(
    value: Any,
    field: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise TranslucentSVGError(
            f"{field} must be a list"
        )

    return value


def _token(
    value: Any,
    field: str,
) -> str:
    token = str(value or "").strip()

    if not token:
        raise TranslucentSVGError(
            f"{field} is required"
        )

    return token


def _finite(
    value: Any,
    field: str,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TranslucentSVGError(
            f"{field} must be numeric"
        ) from exc

    if not math.isfinite(result):
        raise TranslucentSVGError(
            f"{field} must be finite"
        )

    return result


def _positive(
    value: Any,
    field: str,
) -> float:
    result = _finite(
        value,
        field,
    )

    if result <= 0:
        raise TranslucentSVGError(
            f"{field} must be positive"
        )

    return result


def _number(value: Any) -> str:
    number = _finite(
        value,
        "number",
    )

    if number == 0:
        return "0"

    result = format(
        number,
        ".12g",
    )

    return "0" if result == "-0" else result


def _safe_id(value: Any) -> str:
    source = _token(
        value,
        "identifier",
    )

    normalized = "".join(
        character
        if character.isalnum()
        or character in {"-", "_", "."}
        else "-"
        for character in source
    ).strip("-")

    if not normalized:
        raise TranslucentSVGError(
            "identifier normalizes to empty"
        )

    if normalized[0].isdigit():
        normalized = f"tl-{normalized}"

    return normalized


def _paint(
    value: Mapping[str, Any],
) -> dict[str, str]:
    attributes: dict[str, str] = {}

    fill = value.get("fill")
    stroke = value.get("stroke")

    if fill is not None:
        attributes["fill"] = str(fill)

    if stroke is not None:
        attributes["stroke"] = str(stroke)

    stroke_width = value.get(
        "stroke_width"
    )

    if stroke_width is not None:
        width = _finite(
            stroke_width,
            "paint.stroke_width",
        )

        if width < 0:
            raise TranslucentSVGError(
                "paint.stroke_width cannot be negative"
            )

        attributes["stroke-width"] = (
            _number(width)
        )

    for source, target in (
        ("opacity", "opacity"),
        ("fill_opacity", "fill-opacity"),
        ("stroke_opacity", "stroke-opacity"),
    ):
        if source not in value:
            continue

        opacity = _finite(
            value[source],
            f"paint.{source}",
        )

        if opacity < 0 or opacity > 1:
            raise TranslucentSVGError(
                f"paint.{source} must be between 0 and 1"
            )

        attributes[target] = _number(
            opacity
        )

    if "linecap" in value:
        linecap = str(
            value["linecap"]
        )

        if linecap not in {
            "butt",
            "round",
            "square",
        }:
            raise TranslucentSVGError(
                "paint.linecap is invalid"
            )

        attributes["stroke-linecap"] = (
            linecap
        )

    if "linejoin" in value:
        linejoin = str(
            value["linejoin"]
        )

        if linejoin not in {
            "arcs",
            "bevel",
            "miter",
            "miter-clip",
            "round",
        }:
            raise TranslucentSVGError(
                "paint.linejoin is invalid"
            )

        attributes["stroke-linejoin"] = (
            linejoin
        )

    return attributes


def _transform(
    value: Mapping[str, Any],
) -> str:
    x = _finite(
        value.get("x", 0),
        "transform.x",
    )

    y = _finite(
        value.get("y", 0),
        "transform.y",
    )

    rotate = _finite(
        value.get("rotate", 0),
        "transform.rotate",
    )

    scale_x = _finite(
        value.get("scale_x", 1),
        "transform.scale_x",
    )

    scale_y = _finite(
        value.get("scale_y", 1),
        "transform.scale_y",
    )

    skew_x = _finite(
        value.get("skew_x", 0),
        "transform.skew_x",
    )

    skew_y = _finite(
        value.get("skew_y", 0),
        "transform.skew_y",
    )

    operations: list[str] = []

    if x != 0 or y != 0:
        operations.append(
            "translate("
            f"{_number(x)} {_number(y)}"
            ")"
        )

    if rotate != 0:
        operations.append(
            f"rotate({_number(rotate)})"
        )

    if skew_x != 0:
        operations.append(
            f"skewX({_number(skew_x)})"
        )

    if skew_y != 0:
        operations.append(
            f"skewY({_number(skew_y)})"
        )

    if scale_x != 1 or scale_y != 1:
        operations.append(
            "scale("
            f"{_number(scale_x)} "
            f"{_number(scale_y)}"
            ")"
        )

    return " ".join(operations)


def _points(value: Any) -> str:
    points = _list(
        value,
        "geometry.points",
    )

    if len(points) > max_points:
        raise TranslucentSVGError(
            "blot geometry point limit exceeded"
        )

    result: list[str] = []

    for index, point in enumerate(points):
        if (
            not isinstance(
                point,
                (list, tuple),
            )
            or len(point) != 2
        ):
            raise TranslucentSVGError(
                f"geometry.points[{index}] must contain x and y"
            )

        result.append(
            f"{_number(point[0])},"
            f"{_number(point[1])}"
        )

    return " ".join(result)


def _geometry(
    shard: Mapping[str, Any],
) -> ET.Element:
    kind = _token(
        shard.get("kind"),
        "shard.kind",
    )

    if kind not in supported_geometry:
        raise TranslucentSVGError(
            f"unsupported blot geometry kind: {kind}"
        )

    shard_id = _safe_id(
        shard.get("shard_id")
        or shard.get("id")
    )

    parameters = _mapping(
        shard.get("parameters", {}),
        "shard.parameters",
    )

    if kind == "circle":
        return ET.Element(
            f"{{{SVG_NS}}}circle",
            {
                "id": shard_id,
                "cx": "0",
                "cy": "0",
                "r": _number(
                    _positive(
                        parameters.get(
                            "radius"
                        ),
                        "circle.radius",
                    )
                ),
            },
        )

    if kind == "ellipse":
        return ET.Element(
            f"{{{SVG_NS}}}ellipse",
            {
                "id": shard_id,
                "cx": "0",
                "cy": "0",
                "rx": _number(
                    _positive(
                        parameters.get("rx"),
                        "ellipse.rx",
                    )
                ),
                "ry": _number(
                    _positive(
                        parameters.get("ry"),
                        "ellipse.ry",
                    )
                ),
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
            parameters.get("radius", 0),
            "rect.radius",
        )

        if radius < 0:
            raise TranslucentSVGError(
                "rect.radius cannot be negative"
            )

        return ET.Element(
            f"{{{SVG_NS}}}rect",
            {
                "id": shard_id,
                "x": _number(-width / 2),
                "y": _number(-height / 2),
                "width": _number(width),
                "height": _number(height),
                "rx": _number(radius),
            },
        )

    if kind == "path":
        return ET.Element(
            f"{{{SVG_NS}}}path",
            {
                "id": shard_id,
                "d": _token(
                    parameters.get("d"),
                    "path.d",
                ),
            },
        )

    points = parameters.get(
        "points"
    )

    if points is None:
        points = shard.get(
            "points"
        )

    if points is None:
        raise TranslucentSVGError(
            f"{kind} requires normalized points"
        )

    return ET.Element(
        f"{{{SVG_NS}}}polygon",
        {
            "id": shard_id,
            "points": _points(points),
        },
    )


def _metadata(
    root: ET.Element,
    *,
    runtime: TranslucentSVGRuntime,
    kind: str,
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
            "kind": kind,
            "renderer": "blot",
            "authority-effect":
                authority_effect,
            "source-digest": str(
                payload.get("digest")
                or _digest(payload)
            ),
        },
    )

    for token, lexeme_id in sorted(
        runtime.semantic_terms().items()
    ):
        ET.SubElement(
            projection,
            f"{{{TL_NS}}}term",
            {
                "token": token,
                "ref": lexeme_id,
            },
        )


def render(
    kind: str,
    payload: Mapping[str, Any],
    context: Mapping[str, Any],
    runtime: TranslucentSVGRuntime,
) -> str:
    if kind not in {
        "blot",
        "geometry",
        "geometry-projection",
    }:
        raise TranslucentSVGError(
            f"blot renderer cannot render {kind!r}"
        )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise TranslucentSVGError(
            "blot payload must be a mapping"
        )

    source_authority_effect = (
        payload.get("authority_effect")
    )

    if source_authority_effect not in {
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
        context.get(
            "width",
            payload.get("width", 1024),
        ),
        "width",
    )

    height = _positive(
        context.get(
            "height",
            payload.get("height", 1024),
        ),
        "height",
    )

    shards = _list(
        payload.get("shards", []),
        "shards",
    )

    instances = _list(
        payload.get("instances", []),
        "instances",
    )

    segues = _list(
        payload.get("segues", []),
        "segues",
    )

    if len(shards) > max_shards:
        raise TranslucentSVGError(
            "blot shard limit exceeded"
        )

    if len(instances) > max_instances:
        raise TranslucentSVGError(
            "blot instance limit exceeded"
        )

    if len(segues) > max_segues:
        raise TranslucentSVGError(
            "blot segue limit exceeded"
        )

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox":
                f"{_number(-width / 2)} "
                f"{_number(-height / 2)} "
                f"{_number(width)} "
                f"{_number(height)}",
            "width": _number(width),
            "height": _number(height),
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
        "A deterministic non-authoritative "
        "projection of reusable Translucent "
        "geometry substance."
    )

    _metadata(
        root,
        runtime=runtime,
        kind=kind,
        payload=payload,
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

        shard_id = _safe_id(
            shard.get("shard_id")
            or shard.get("id")
        )

        if shard_id in shard_ids:
            raise TranslucentSVGError(
                f"duplicate blot shard id: {shard_id}"
            )

        shard_ids.add(
            shard_id
        )

        defs.append(
            _geometry(shard)
        )

    instance_ids: set[str] = set()

    for index, item in enumerate(
        instances
    ):
        instance = _mapping(
            item,
            f"instances[{index}]",
        )

        instance_id = _safe_id(
            instance.get("instance_id")
            or instance.get("id")
        )

        if instance_id in instance_ids:
            raise TranslucentSVGError(
                f"duplicate blot instance id: {instance_id}"
            )

        instance_ids.add(
            instance_id
        )

        shard_id = _safe_id(
            instance.get("shard_id")
        )

        if shard_id not in shard_ids:
            raise TranslucentSVGError(
                f"unknown blot shard: {shard_id}"
            )

        attributes = {
            "id": instance_id,
            "href": f"#{shard_id}",
        }

        paint = _mapping(
            instance.get("paint", {}),
            f"instances[{index}].paint",
        )

        attributes.update(
            _paint(paint)
        )

        transform = _mapping(
            instance.get(
                "transform",
                {},
            ),
            f"instances[{index}].transform",
        )

        transform_text = _transform(
            transform
        )

        if transform_text:
            attributes["transform"] = (
                transform_text
            )

        ET.SubElement(
            root,
            f"{{{SVG_NS}}}use",
            attributes,
        )

    for index, item in enumerate(
        segues
    ):
        segue = _mapping(
            item,
            f"segues[{index}]",
        )

        segue_kind = _token(
            segue.get("kind"),
            f"segues[{index}].kind",
        )

        source = _safe_id(
            segue.get("source")
        )

        target = _safe_id(
            segue.get("target")
        )

        if source not in instance_ids:
            raise TranslucentSVGError(
                f"unknown segue source: {source}"
            )

        if target not in instance_ids:
            raise TranslucentSVGError(
                f"unknown segue target: {target}"
            )

        if not segue_kind:
            raise TranslucentSVGError(
                "segue kind is required"
            )

    rendered = ET.tostring(
        root,
        encoding="unicode",
        short_empty_elements=True,
    )

    runtime.parse(
        rendered
    )

    return rendered


def register(
    runtime: TranslucentSVGRuntime,
    *,
    replace: bool = False,
) -> None:
    runtime.register_renderer(
        "blot",
        render,
        replace=replace,
    )


def manifest() -> dict[str, Any]:
    result = {
        "schema": schema,
        "owner": owner,
        "kind":
            "translucent-svg-blot-projection",
        "renderer": "blot",
        "authority_effect":
            authority_effect,
        "projection_only": True,
        "authoritative": False,
        "supported_geometry":
            sorted(supported_geometry),
        "limits": {
            "max_shards": max_shards,
            "max_instances":
                max_instances,
            "max_segues": max_segues,
            "max_points": max_points,
        },
    }

    result["digest"] = _digest(
        result
    )

    return result


def selftest(
    runtime: TranslucentSVGRuntime,
) -> dict[str, Any]:
    register(
        runtime,
        replace=True,
    )

    payload: dict[str, Any] = {
        "authority_effect": "none",
        "projection_only": True,
        "authoritative": False,
        "width": 320,
        "height": 240,
        "shards": [
            {
                "kind": "circle",
                "shard_id":
                    "geometry-circle",
                "parameters": {
                    "radius": 24,
                },
            },
        ],
        "instances": [
            {
                "instance_id":
                    "geometry-instance-a",
                "shard_id":
                    "geometry-circle",
                "transform": {
                    "x": -32,
                    "y": 0,
                    "scale_x": 1,
                    "scale_y": 1,
                },
                "paint": {
                    "fill": "#d9b44a",
                    "stroke": "#11151a",
                    "stroke_width": 2,
                },
            },
            {
                "instance_id":
                    "geometry-instance-b",
                "shard_id":
                    "geometry-circle",
                "transform": {
                    "x": 32,
                    "y": 0,
                    "scale_x": -1,
                    "scale_y": 1,
                },
                "paint": {
                    "fill": "#d9b44a",
                    "stroke": "#11151a",
                    "stroke_width": 2,
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
            },
        ],
    }

    payload["digest"] = _digest(
        payload
    )

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

    root = runtime.parse(
        first
    )

    defs = root.find(
        f"{{{SVG_NS}}}defs"
    )

    uses = root.findall(
        f"{{{SVG_NS}}}use"
    )

    checks = {
        "schema_exact":
            schema
            == "savant.translucent.svg.blot.v1",
        "authority_none":
            authority_effect
            == "none",
        "renderer_registered":
            "blot"
            in runtime.renderer_names(),
        "deterministic":
            first == second,
        "single_substance":
            defs is not None
            and len(list(defs)) == 1,
        "instance_reuse":
            len(uses) == 2,
        "mirror_segue":
            payload["segues"][0]["kind"]
            == "mirror",
        "projection_only":
            payload["projection_only"]
            is True,
        "non_authoritative":
            payload["authoritative"]
            is False,
        "valid_svg":
            root.tag
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

    result["digest"] = _digest(
        result
    )

    return result


__all__ = [
    "authority_effect",
    "manifest",
    "owner",
    "register",
    "render",
    "schema",
    "selftest",
    "supported_geometry",
]
