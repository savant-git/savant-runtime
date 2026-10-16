#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import html
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


NAME = "blot."
SCHEMA = "savant.translucent.blot.v1"
AUTHORITY_EFFECT = "none"
SVG_NS = "http://www.w3.org/2000/svg"

MAX_SHARDS = 100_000
MAX_INSTANCES = 1_000_000
MAX_POINTS = 1_000_000
MAX_DEPTH = 64

TAU = math.tau


class BlotError(ValueError):
    pass


def _finite(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BlotError(f"{name} must be numeric") from exc

    if not math.isfinite(result):
        raise BlotError(f"{name} must be finite")

    return result


def _positive(value: Any, name: str) -> float:
    result = _finite(value, name)

    if result <= 0:
        raise BlotError(f"{name} must be greater than zero")

    return result


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


def _esc(value: Any) -> str:
    return html.escape(
        str(value),
        quote=True,
    )


def _num(value: float) -> str:
    value = _finite(value, "number")

    if value == 0:
        return "0"

    text = format(value, ".12g")

    if text == "-0":
        return "0"

    return text


@dataclass(frozen=True)
class Transform:
    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotate: float = 0.0
    skew_x: float = 0.0
    skew_y: float = 0.0

    def normalized(self) -> dict[str, float]:
        return {
            "x": _finite(self.x, "x"),
            "y": _finite(self.y, "y"),
            "scale_x": _finite(self.scale_x, "scale_x"),
            "scale_y": _finite(self.scale_y, "scale_y"),
            "rotate": _finite(self.rotate, "rotate"),
            "skew_x": _finite(self.skew_x, "skew_x"),
            "skew_y": _finite(self.skew_y, "skew_y"),
        }

    def svg(self) -> str:
        n = self.normalized()

        operations: list[str] = []

        if n["x"] or n["y"]:
            operations.append(
                f'translate({_num(n["x"])} {_num(n["y"])})'
            )

        if n["rotate"]:
            operations.append(
                f'rotate({_num(n["rotate"])})'
            )

        if n["skew_x"]:
            operations.append(
                f'skewX({_num(n["skew_x"])})'
            )

        if n["skew_y"]:
            operations.append(
                f'skewY({_num(n["skew_y"])})'
            )

        if n["scale_x"] != 1 or n["scale_y"] != 1:
            operations.append(
                "scale("
                f'{_num(n["scale_x"])} '
                f'{_num(n["scale_y"])}'
                ")"
            )

        return " ".join(operations)


@dataclass(frozen=True)
class Paint:
    fill: str = "none"
    stroke: str = "currentColor"
    stroke_width: float = 1.0
    opacity: float = 1.0
    linecap: str = "round"
    linejoin: str = "round"

    def attrs(self) -> str:
        width = _positive(
            self.stroke_width,
            "stroke_width",
        )

        opacity = _finite(
            self.opacity,
            "opacity",
        )

        if not 0 <= opacity <= 1:
            raise BlotError(
                "opacity must be between zero and one"
            )

        if self.linecap not in {
            "butt",
            "round",
            "square",
        }:
            raise BlotError(
                f"unsupported linecap: {self.linecap}"
            )

        if self.linejoin not in {
            "arcs",
            "bevel",
            "miter",
            "miter-clip",
            "round",
        }:
            raise BlotError(
                f"unsupported linejoin: {self.linejoin}"
            )

        return (
            f'fill="{_esc(self.fill)}" '
            f'stroke="{_esc(self.stroke)}" '
            f'stroke-width="{_num(width)}" '
            f'opacity="{_num(opacity)}" '
            f'stroke-linecap="{_esc(self.linecap)}" '
            f'stroke-linejoin="{_esc(self.linejoin)}"'
        )


@dataclass(frozen=True)
class GeometryShard:
    kind: str
    parameters: Mapping[str, Any]
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    @property
    def substance(self) -> dict[str, Any]:
        return {
            "schema": f"{SCHEMA}.geometry-shard",
            "kind": self.kind,
            "parameters": dict(self.parameters),
            "provenance": list(self.provenance),
            "lineage": list(self.lineage),
        }

    @property
    def digest(self) -> str:
        return _digest(self.substance)

    @property
    def shard_id(self) -> str:
        return f"blot-{self.digest[:24]}"


@dataclass(frozen=True)
class GeometryInstance:
    shard_id: str
    transform: Transform = Transform()
    paint: Paint = Paint()
    instance_id: str | None = None

    def normalized(self) -> dict[str, Any]:
        substance = {
            "shard_id": self.shard_id,
            "transform": self.transform.normalized(),
            "paint": {
                "fill": self.paint.fill,
                "stroke": self.paint.stroke,
                "stroke_width": self.paint.stroke_width,
                "opacity": self.paint.opacity,
                "linecap": self.paint.linecap,
                "linejoin": self.paint.linejoin,
            },
        }

        instance_id = (
            self.instance_id
            or f"instance-{_digest(substance)[:24]}"
        )

        return {
            "instance_id": instance_id,
            **substance,
        }


@dataclass(frozen=True)
class GeometrySegue:
    kind: str
    source: str
    target: str
    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "target": self.target,
            "parameters": dict(self.parameters),
        }


def circle(radius: float) -> GeometryShard:
    return GeometryShard(
        "circle",
        {
            "radius": _positive(
                radius,
                "radius",
            ),
        },
    )


def ellipse(
    rx: float,
    ry: float,
) -> GeometryShard:
    return GeometryShard(
        "ellipse",
        {
            "rx": _positive(rx, "rx"),
            "ry": _positive(ry, "ry"),
        },
    )


def rect(
    width: float,
    height: float,
    radius: float = 0.0,
) -> GeometryShard:
    width = _positive(width, "width")
    height = _positive(height, "height")
    radius = _finite(radius, "radius")

    if radius < 0:
        raise BlotError(
            "radius cannot be negative"
        )

    return GeometryShard(
        "rect",
        {
            "width": width,
            "height": height,
            "radius": radius,
        },
    )


def polygon(
    radius: float,
    sides: int,
    phase: float = -90.0,
) -> GeometryShard:
    radius = _positive(radius, "radius")

    if not isinstance(sides, int) or sides < 3:
        raise BlotError(
            "polygon sides must be an integer >= 3"
        )

    return GeometryShard(
        "polygon",
        {
            "radius": radius,
            "sides": sides,
            "phase": _finite(
                phase,
                "phase",
            ),
        },
    )


def star(
    outer: float,
    inner: float,
    points: int,
    phase: float = -90.0,
) -> GeometryShard:
    outer = _positive(outer, "outer")
    inner = _positive(inner, "inner")

    if inner >= outer:
        raise BlotError(
            "star inner radius must be smaller "
            "than outer radius"
        )

    if not isinstance(points, int) or points < 2:
        raise BlotError(
            "star points must be an integer >= 2"
        )

    return GeometryShard(
        "star",
        {
            "outer": outer,
            "inner": inner,
            "points": points,
            "phase": _finite(
                phase,
                "phase",
            ),
        },
    )


def superellipse(
    a: float,
    b: float,
    n: float,
    samples: int = 192,
) -> GeometryShard:
    a = _positive(a, "a")
    b = _positive(b, "b")
    n = _positive(n, "n")

    if not isinstance(samples, int):
        raise BlotError(
            "samples must be an integer"
        )

    if not 16 <= samples <= 8192:
        raise BlotError(
            "samples must be between 16 and 8192"
        )

    return GeometryShard(
        "superellipse",
        {
            "a": a,
            "b": b,
            "n": n,
            "samples": samples,
        },
    )


def superformula(
    radius: float,
    m: float,
    n1: float,
    n2: float,
    n3: float,
    a: float = 1.0,
    b: float = 1.0,
    samples: int = 512,
) -> GeometryShard:
    radius = _positive(radius, "radius")
    a = _positive(a, "a")
    b = _positive(b, "b")
    n1 = _finite(n1, "n1")
    n2 = _finite(n2, "n2")
    n3 = _finite(n3, "n3")

    if n1 == 0:
        raise BlotError(
            "n1 cannot be zero"
        )

    if not isinstance(samples, int):
        raise BlotError(
            "samples must be an integer"
        )

    if not 32 <= samples <= 8192:
        raise BlotError(
            "samples must be between 32 and 8192"
        )

    return GeometryShard(
        "superformula",
        {
            "radius": radius,
            "m": _finite(m, "m"),
            "n1": n1,
            "n2": n2,
            "n3": n3,
            "a": a,
            "b": b,
            "samples": samples,
        },
    )


def path(
    d: str,
) -> GeometryShard:
    if not isinstance(d, str) or not d.strip():
        raise BlotError(
            "path data must be non-empty"
        )

    if len(d) > 4_000_000:
        raise BlotError(
            "path data exceeds blot. resource limit"
        )

    return GeometryShard(
        "path",
        {
            "d": d.strip(),
        },
    )


def _points(
    values: Iterable[
        tuple[float, float]
    ],
) -> str:
    return " ".join(
        f"{_num(x)},{_num(y)}"
        for x, y in values
    )


def _polygon_points(
    radius: float,
    sides: int,
    phase: float,
) -> list[tuple[float, float]]:
    phase_radians = math.radians(phase)

    return [
        (
            radius
            * math.cos(
                phase_radians
                + TAU * index / sides
            ),
            radius
            * math.sin(
                phase_radians
                + TAU * index / sides
            ),
        )
        for index in range(sides)
    ]


def _star_points(
    outer: float,
    inner: float,
    count: int,
    phase: float,
) -> list[tuple[float, float]]:
    phase_radians = math.radians(phase)
    total = count * 2

    result = []

    for index in range(total):
        radius = (
            outer
            if index % 2 == 0
            else inner
        )

        angle = (
            phase_radians
            + TAU * index / total
        )

        result.append(
            (
                radius * math.cos(angle),
                radius * math.sin(angle),
            )
        )

    return result


def _superellipse_points(
    a: float,
    b: float,
    n: float,
    samples: int,
) -> list[tuple[float, float]]:
    power = 2.0 / n
    result = []

    for index in range(samples):
        t = TAU * index / samples

        c = math.cos(t)
        s = math.sin(t)

        x = (
            a
            * math.copysign(
                abs(c) ** power,
                c,
            )
        )

        y = (
            b
            * math.copysign(
                abs(s) ** power,
                s,
            )
        )

        result.append((x, y))

    return result


def _superformula_points(
    parameters: Mapping[str, Any],
) -> list[tuple[float, float]]:
    radius = float(parameters["radius"])
    m = float(parameters["m"])
    n1 = float(parameters["n1"])
    n2 = float(parameters["n2"])
    n3 = float(parameters["n3"])
    a = float(parameters["a"])
    b = float(parameters["b"])
    samples = int(parameters["samples"])

    result = []

    for index in range(samples):
        phi = TAU * index / samples

        first = abs(
            math.cos(m * phi / 4.0) / a
        ) ** n2

        second = abs(
            math.sin(m * phi / 4.0) / b
        ) ** n3

        total = first + second

        if total == 0:
            r = 0.0
        else:
            r = total ** (-1.0 / n1)

        r *= radius

        x = r * math.cos(phi)
        y = r * math.sin(phi)

        if not (
            math.isfinite(x)
            and math.isfinite(y)
        ):
            raise BlotError(
                "superformula produced "
                "non-finite geometry"
            )

        result.append((x, y))

    return result


class Blot:
    def __init__(
        self,
        width: float = 1024,
        height: float = 1024,
    ) -> None:
        self.width = _positive(
            width,
            "width",
        )

        self.height = _positive(
            height,
            "height",
        )

        self._shards: dict[
            str,
            GeometryShard,
        ] = {}

        self._instances: list[
            GeometryInstance
        ] = []

        self._segues: list[
            GeometrySegue
        ] = []

    def substantiate(
        self,
        shard: GeometryShard,
    ) -> str:
        if len(self._shards) >= MAX_SHARDS:
            raise BlotError(
                "geometry shard limit exceeded"
            )

        shard_id = shard.shard_id

        existing = self._shards.get(
            shard_id
        )

        if (
            existing is not None
            and existing.digest != shard.digest
        ):
            raise BlotError(
                "geometry shard identity conflict"
            )

        self._shards[shard_id] = shard

        return shard_id

    def instance(
        self,
        shard: GeometryShard | str,
        *,
        transform: Transform = Transform(),
        paint: Paint = Paint(),
        instance_id: str | None = None,
    ) -> str:
        if len(self._instances) >= MAX_INSTANCES:
            raise BlotError(
                "geometry instance limit exceeded"
            )

        if isinstance(
            shard,
            GeometryShard,
        ):
            shard_id = self.substantiate(
                shard
            )
        else:
            shard_id = str(shard)

        if shard_id not in self._shards:
            raise BlotError(
                f"unknown geometry shard: {shard_id}"
            )

        instance = GeometryInstance(
            shard_id=shard_id,
            transform=transform,
            paint=paint,
            instance_id=instance_id,
        )

        normalized = instance.normalized()

        existing_ids = {
            item.normalized()["instance_id"]
            for item in self._instances
        }

        if (
            normalized["instance_id"]
            in existing_ids
        ):
            raise BlotError(
                "duplicate geometry instance id"
            )

        self._instances.append(instance)

        return normalized["instance_id"]

    def relate(
        self,
        kind: str,
        source: str,
        target: str,
        **parameters: Any,
    ) -> None:
        instance_ids = {
            item.normalized()["instance_id"]
            for item in self._instances
        }

        if source not in instance_ids:
            raise BlotError(
                f"unknown segue source: {source}"
            )

        if target not in instance_ids:
            raise BlotError(
                f"unknown segue target: {target}"
            )

        self._segues.append(
            GeometrySegue(
                kind=str(kind),
                source=source,
                target=target,
                parameters=parameters,
            )
        )

    def radial(
        self,
        shard: GeometryShard | str,
        *,
        count: int,
        radius: float,
        paint: Paint = Paint(),
        rotate_instances: bool = True,
        phase: float = 0.0,
    ) -> list[str]:
        if not isinstance(count, int):
            raise BlotError(
                "radial count must be an integer"
            )

        if not 1 <= count <= 100_000:
            raise BlotError(
                "radial count outside resource bounds"
            )

        radius = _finite(
            radius,
            "radius",
        )

        phase = _finite(
            phase,
            "phase",
        )

        result = []

        for index in range(count):
            angle = (
                phase
                + 360.0 * index / count
            )

            radians = math.radians(
                angle
            )

            x = radius * math.cos(radians)
            y = radius * math.sin(radians)

            result.append(
                self.instance(
                    shard,
                    transform=Transform(
                        x=x,
                        y=y,
                        rotate=(
                            angle
                            if rotate_instances
                            else 0.0
                        ),
                    ),
                    paint=paint,
                )
            )

        return result

    def mirror(
        self,
        instance_id: str,
        *,
        axis: str = "x",
    ) -> str:
        source = None

        for instance in self._instances:
            normalized = instance.normalized()

            if (
                normalized["instance_id"]
                == instance_id
            ):
                source = instance
                break

        if source is None:
            raise BlotError(
                f"unknown instance: {instance_id}"
            )

        t = source.transform

        if axis == "x":
            transform = Transform(
                x=t.x,
                y=t.y,
                scale_x=t.scale_x,
                scale_y=-t.scale_y,
                rotate=t.rotate,
                skew_x=t.skew_x,
                skew_y=t.skew_y,
            )

        elif axis == "y":
            transform = Transform(
                x=t.x,
                y=t.y,
                scale_x=-t.scale_x,
                scale_y=t.scale_y,
                rotate=t.rotate,
                skew_x=t.skew_x,
                skew_y=t.skew_y,
            )

        else:
            raise BlotError(
                "mirror axis must be x or y"
            )

        mirrored = self.instance(
            source.shard_id,
            transform=transform,
            paint=source.paint,
        )

        self.relate(
            "mirror",
            instance_id,
            mirrored,
            axis=axis,
        )

        return mirrored

    def _geometry_svg(
        self,
        shard: GeometryShard,
    ) -> str:
        p = shard.parameters

        if shard.kind == "circle":
            return (
                f'<circle id="{shard.shard_id}" '
                f'cx="0" cy="0" '
                f'r="{_num(float(p["radius"]))}" />'
            )

        if shard.kind == "ellipse":
            return (
                f'<ellipse id="{shard.shard_id}" '
                f'cx="0" cy="0" '
                f'rx="{_num(float(p["rx"]))}" '
                f'ry="{_num(float(p["ry"]))}" />'
            )

        if shard.kind == "rect":
            width = float(p["width"])
            height = float(p["height"])
            radius = float(p["radius"])

            return (
                f'<rect id="{shard.shard_id}" '
                f'x="{_num(-width / 2)}" '
                f'y="{_num(-height / 2)}" '
                f'width="{_num(width)}" '
                f'height="{_num(height)}" '
                f'rx="{_num(radius)}" />'
            )

        if shard.kind == "polygon":
            points = _polygon_points(
                float(p["radius"]),
                int(p["sides"]),
                float(p["phase"]),
            )

            return (
                f'<polygon id="{shard.shard_id}" '
                f'points="{_points(points)}" />'
            )

        if shard.kind == "star":
            points = _star_points(
                float(p["outer"]),
                float(p["inner"]),
                int(p["points"]),
                float(p["phase"]),
            )

            return (
                f'<polygon id="{shard.shard_id}" '
                f'points="{_points(points)}" />'
            )

        if shard.kind == "superellipse":
            points = _superellipse_points(
                float(p["a"]),
                float(p["b"]),
                float(p["n"]),
                int(p["samples"]),
            )

            return (
                f'<polygon id="{shard.shard_id}" '
                f'points="{_points(points)}" />'
            )

        if shard.kind == "superformula":
            points = _superformula_points(p)

            return (
                f'<polygon id="{shard.shard_id}" '
                f'points="{_points(points)}" />'
            )

        if shard.kind == "path":
            return (
                f'<path id="{shard.shard_id}" '
                f'd="{_esc(p["d"])}" />'
            )

        raise BlotError(
            f"unsupported geometry shard: {shard.kind}"
        )

    def manifest(self) -> dict[str, Any]:
        shards = [
            self._shards[key].substance
            | {
                "shard_id": key,
                "digest":
                    self._shards[key].digest,
            }
            for key in sorted(self._shards)
        ]

        instances = [
            item.normalized()
            for item in self._instances
        ]

        segues = [
            item.normalized()
            for item in self._segues
        ]

        body = {
            "schema": SCHEMA,
            "name": NAME,
            "authority_effect":
                AUTHORITY_EFFECT,
            "projection_only": True,
            "authoritative": False,
            "width": self.width,
            "height": self.height,
            "shards": shards,
            "instances": instances,
            "segues": segues,
        }

        return {
            **body,
            "digest": _digest(body),
        }

    def render(self) -> str:
        manifest = self.manifest()

        defs = "".join(
            self._geometry_svg(
                self._shards[key]
            )
            for key in sorted(self._shards)
        )

        uses = []

        for instance in self._instances:
            normalized = instance.normalized()
            transform = instance.transform.svg()

            attrs = [
                f'id="{_esc(normalized["instance_id"])}"',
                (
                    'href="#'
                    f'{_esc(instance.shard_id)}"'
                ),
                instance.paint.attrs(),
            ]

            if transform:
                attrs.append(
                    f'transform="{_esc(transform)}"'
                )

            uses.append(
                "<use "
                + " ".join(attrs)
                + " />"
            )

        metadata = _esc(
            _canonical(
                {
                    "schema": SCHEMA,
                    "name": NAME,
                    "digest":
                        manifest["digest"],
                    "authority_effect":
                        AUTHORITY_EFFECT,
                    "projection_only": True,
                }
            )
        )

        return (
            f'<svg xmlns="{SVG_NS}" '
            f'viewBox="'
            f'{_num(-self.width / 2)} '
            f'{_num(-self.height / 2)} '
            f'{_num(self.width)} '
            f'{_num(self.height)}">'
            f"<metadata>{metadata}</metadata>"
            f"<defs>{defs}</defs>"
            f'{"".join(uses)}'
            "</svg>"
        )


def selftest() -> dict[str, Any]:
    blot = Blot(
        width=800,
        height=800,
    )

    petal = superformula(
        radius=90,
        m=6,
        n1=0.35,
        n2=1.7,
        n3=1.7,
        samples=256,
    )

    petal_id = blot.substantiate(
        petal
    )

    instances = blot.radial(
        petal_id,
        count=24,
        radius=210,
        paint=Paint(
            fill="none",
            stroke="currentColor",
            stroke_width=1.5,
            opacity=0.72,
        ),
    )

    mirrored = blot.mirror(
        instances[0],
        axis="y",
    )

    first = blot.render()
    second = blot.render()

    manifest = blot.manifest()

    checks = {
        "name_exact":
            NAME == "blot.",

        "authority_none":
            manifest["authority_effect"]
            == "none",

        "projection_only":
            manifest["projection_only"]
            is True,

        "non_authoritative":
            manifest["authoritative"]
            is False,

        "substance_once":
            len(manifest["shards"])
            == 1,

        "instances_reuse_substance":
            len(manifest["instances"])
            == 25,

        "typed_geometry_segue":
            any(
                segue["kind"] == "mirror"
                for segue in manifest["segues"]
            ),

        "svg_symbolic_reuse":
            first.count("<use ") == 25,

        "single_geometry_definition":
            first.count(
                f'id="{petal_id}"'
            ) == 1,

        "deterministic_render":
            first == second,

        "stable_manifest":
            manifest == blot.manifest(),

        "complex_geometry":
            "polygon" in first,

        "metadata_bound":
            manifest["digest"] in first,

        "mirror_created":
            mirrored
            in {
                item["instance_id"]
                for item
                in manifest["instances"]
            },
    }

    return {
        "schema":
            f"{SCHEMA}.selftest",

        "ok":
            all(checks.values()),

        "checks":
            checks,

        "manifest_digest":
            manifest["digest"],

        "svg_digest":
            hashlib.sha256(
                first.encode("utf-8")
            ).hexdigest(),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
