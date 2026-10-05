"""
SAVANT Filament Vector Renderer
Canonical deterministic geometry kernel.

This module owns the native geometry primitives required by the
Filament vector projection runtime.

Architectural rules implemented here:

* canonical geometry is semantic substance, not serialized SVG syntax;
* all semantic numbers are finite real numbers;
* computational tolerances are centralized;
* negative zero is normalized;
* points, vectors, bounds, transforms, commands, paths, and segments are
  immutable;
* affine transform multiplication order is explicit;
* canonical path commands are limited to move, line, quadratic Bézier,
  cubic Bézier, elliptical arc, and close;
* subpath boundaries and closure remain explicit;
* quadratic and cubic Bézier extrema are calculated analytically;
* SVG endpoint-form elliptical arcs are converted deterministically to
  center form when derived mathematics requires it;
* arc bounds include true rotated-ellipse extrema;
* path metrics are derived lazily;
* curve length uses deterministic adaptive numerical integration;
* arc-to-cubic conversion is explicitly approximation-bearing derived
  geometry and carries tolerance/error metadata;
* arbitrary affine transformation of arcs falls back to canonical cubic
  approximation when exact preservation is not justified;
* flattening is deterministic and tolerance-bound;
* ordinary SVG projection does not require stroke-to-path conversion;
* general boolean geometry is exposed only through a backend-neutral
  contract and is deliberately not faked by the native kernel.

This module has no third-party dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
import math
from numbers import Real
from typing import Final, Protocol, Self, TypeAlias, overload, runtime_checkable


try:
    from .errors import (
        ArcGeometryError,
        BoundsError,
        DegenerateGeometryError,
        DiagnosticPath,
        GeometryBackendError,
        InvalidGeometryError,
        InvalidTransformError,
        NonFiniteGeometryError,
        PathGeometryError,
        PathTopologyError,
        SingularTransformError,
        UnsupportedFeatureError,
    )
except ImportError:
    from errors import (
        ArcGeometryError,
        BoundsError,
        DegenerateGeometryError,
        DiagnosticPath,
        GeometryBackendError,
        InvalidGeometryError,
        InvalidTransformError,
        NonFiniteGeometryError,
        PathGeometryError,
        PathTopologyError,
        SingularTransformError,
        UnsupportedFeatureError,
    )


GEOMETRY_SCHEMA: Final[str] = (
    "savant://filament/vector/geometry/1.0.0"
)

PATH_SCHEMA: Final[str] = (
    "savant://filament/vector/path/1.0.0"
)

MODULE_VERSION: Final[str] = "1.0.0"

TAU: Final[float] = math.tau
PI: Final[float] = math.pi
HALF_PI: Final[float] = math.pi / 2.0


# ---------------------------------------------------------------------------
# Numeric policy
# ---------------------------------------------------------------------------


def _finite_real(
    value: Real,
    *,
    name: str,
    path: str | DiagnosticPath = "scene",
) -> float:
    """
    Convert one semantic real number to a finite float.

    Canonical scene geometry intentionally does not accept numeric strings.
    Parsers may normalize textual numbers before constructing canonical
    geometry.
    """

    if isinstance(value, bool) or not isinstance(value, Real):
        raise NonFiniteGeometryError(
            f"{name} must be a finite real number",
            path=path,
            context={
                "name": name,
                "received_type": type(value).__name__,
            },
        )

    result = float(value)

    if not math.isfinite(result):
        raise NonFiniteGeometryError(
            f"{name} must be finite",
            path=path,
            context={
                "name": name,
            },
        )

    if result == 0.0:
        return 0.0

    return result


def _positive_finite(
    value: Real,
    *,
    name: str,
    path: str | DiagnosticPath = "scene",
    allow_zero: bool = False,
) -> float:
    result = _finite_real(
        value,
        name=name,
        path=path,
    )

    if allow_zero:
        valid = result >= 0.0
    else:
        valid = result > 0.0

    if not valid:
        comparator = "non-negative" if allow_zero else "positive"

        raise InvalidGeometryError(
            f"{name} must be {comparator}",
            path=path,
            context={
                "name": name,
                "value": result,
            },
        )

    return result


def normalize_zero(value: float) -> float:
    """
    Canonicalize negative zero.

    SVG serialization later uses the same semantic convention.
    """

    return 0.0 if value == 0.0 else value


def clamp(
    value: float,
    lower: float,
    upper: float,
) -> float:
    if lower > upper:
        raise ValueError(
            "clamp lower bound must not exceed upper bound"
        )

    return max(
        lower,
        min(upper, value),
    )


def lerp_scalar(
    start: float,
    end: float,
    t: float,
) -> float:
    return start + (end - start) * t


def normalize_angle_radians(
    angle: float,
) -> float:
    result = math.fmod(
        angle,
        TAU,
    )

    if result < 0.0:
        result += TAU

    if result == TAU:
        return 0.0

    return normalize_zero(result)


def normalize_degrees(
    degrees: float,
) -> float:
    result = math.fmod(
        degrees,
        360.0,
    )

    if result <= -180.0:
        result += 360.0
    elif result > 180.0:
        result -= 360.0

    return normalize_zero(result)


@dataclass(frozen=True, slots=True)
class TolerancePolicy:
    """
    Centralized deterministic computational tolerance policy.

    Semantic scene coordinates remain exact inputs. These tolerances apply
    only to derived computation such as root classification, numerical
    integration, curve flattening, and approximation.
    """

    epsilon: float = 1.0e-12
    angle_epsilon: float = 1.0e-12
    length_tolerance: float = 1.0e-8
    flattening_tolerance: float = 1.0e-4
    arc_approximation_tolerance: float = 1.0e-5
    max_integration_depth: int = 24
    max_flattening_depth: int = 24
    max_arc_approximation_depth: int = 20

    def __post_init__(self) -> None:
        for name in (
            "epsilon",
            "angle_epsilon",
            "length_tolerance",
            "flattening_tolerance",
            "arc_approximation_tolerance",
        ):
            value = _positive_finite(
                getattr(self, name),
                name=name,
                path="geometry/tolerance",
            )

            object.__setattr__(
                self,
                name,
                value,
            )

        for name in (
            "max_integration_depth",
            "max_flattening_depth",
            "max_arc_approximation_depth",
        ):
            value = getattr(self, name)

            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise InvalidGeometryError(
                    f"{name} must be an integer",
                    path="geometry/tolerance",
                )

            if value < 1:
                raise InvalidGeometryError(
                    f"{name} must be at least 1",
                    path="geometry/tolerance",
                )

    def near_zero(
        self,
        value: float,
    ) -> bool:
        return abs(value) <= self.epsilon

    def close(
        self,
        left: float,
        right: float,
    ) -> bool:
        scale = max(
            1.0,
            abs(left),
            abs(right),
        )

        return (
            abs(left - right)
            <= self.epsilon * scale
        )


DEFAULT_TOLERANCE: Final[TolerancePolicy] = (
    TolerancePolicy()
)


# ---------------------------------------------------------------------------
# Point and vector primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Vector:
    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "x",
            _finite_real(
                self.x,
                name="vector.x",
                path="geometry/vector",
            ),
        )

        object.__setattr__(
            self,
            "y",
            _finite_real(
                self.y,
                name="vector.y",
                path="geometry/vector",
            ),
        )

    def __add__(
        self,
        other: Vector,
    ) -> Vector:
        if not isinstance(other, Vector):
            return NotImplemented

        return Vector(
            self.x + other.x,
            self.y + other.y,
        )

    def __sub__(
        self,
        other: Vector,
    ) -> Vector:
        if not isinstance(other, Vector):
            return NotImplemented

        return Vector(
            self.x - other.x,
            self.y - other.y,
        )

    def __neg__(self) -> Vector:
        return Vector(
            -self.x,
            -self.y,
        )

    def __mul__(
        self,
        scalar: Real,
    ) -> Vector:
        scalar_value = _finite_real(
            scalar,
            name="scalar",
            path="geometry/vector",
        )

        return Vector(
            self.x * scalar_value,
            self.y * scalar_value,
        )

    def __rmul__(
        self,
        scalar: Real,
    ) -> Vector:
        return self * scalar

    def __truediv__(
        self,
        scalar: Real,
    ) -> Vector:
        scalar_value = _finite_real(
            scalar,
            name="scalar",
            path="geometry/vector",
        )

        if scalar_value == 0.0:
            raise DegenerateGeometryError(
                "cannot divide vector by zero",
                path="geometry/vector",
            )

        return Vector(
            self.x / scalar_value,
            self.y / scalar_value,
        )

    def dot(
        self,
        other: Vector,
    ) -> float:
        return (
            self.x * other.x
            + self.y * other.y
        )

    def cross(
        self,
        other: Vector,
    ) -> float:
        return (
            self.x * other.y
            - self.y * other.x
        )

    @property
    def magnitude_squared(self) -> float:
        return (
            self.x * self.x
            + self.y * self.y
        )

    @property
    def magnitude(self) -> float:
        return math.hypot(
            self.x,
            self.y,
        )

    def normalized(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        magnitude = self.magnitude

        if magnitude <= tolerance.epsilon:
            raise DegenerateGeometryError(
                "cannot normalize a zero-length vector",
                path="geometry/vector",
            )

        return self / magnitude

    def perpendicular_left(self) -> Vector:
        return Vector(
            -self.y,
            self.x,
        )

    def perpendicular_right(self) -> Vector:
        return Vector(
            self.y,
            -self.x,
        )

    def lerp(
        self,
        other: Vector,
        t: Real,
    ) -> Vector:
        t_value = _finite_real(
            t,
            name="t",
            path="geometry/vector",
        )

        return Vector(
            lerp_scalar(
                self.x,
                other.x,
                t_value,
            ),
            lerp_scalar(
                self.y,
                other.y,
                t_value,
            ),
        )

    def transformed(
        self,
        transform: AffineTransform,
    ) -> Vector:
        return transform.apply_vector(
            self
        )


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "x",
            _finite_real(
                self.x,
                name="point.x",
                path="geometry/point",
            ),
        )

        object.__setattr__(
            self,
            "y",
            _finite_real(
                self.y,
                name="point.y",
                path="geometry/point",
            ),
        )

    def __add__(
        self,
        vector: Vector,
    ) -> Point:
        if not isinstance(
            vector,
            Vector,
        ):
            return NotImplemented

        return Point(
            self.x + vector.x,
            self.y + vector.y,
        )

    @overload
    def __sub__(
        self,
        other: Point,
    ) -> Vector:
        ...

    @overload
    def __sub__(
        self,
        other: Vector,
    ) -> Point:
        ...

    def __sub__(
        self,
        other: Point | Vector,
    ) -> Vector | Point:
        if isinstance(
            other,
            Point,
        ):
            return Vector(
                self.x - other.x,
                self.y - other.y,
            )

        if isinstance(
            other,
            Vector,
        ):
            return Point(
                self.x - other.x,
                self.y - other.y,
            )

        return NotImplemented

    def distance_to(
        self,
        other: Point,
    ) -> float:
        return math.hypot(
            other.x - self.x,
            other.y - self.y,
        )

    def distance_squared_to(
        self,
        other: Point,
    ) -> float:
        dx = other.x - self.x
        dy = other.y - self.y

        return dx * dx + dy * dy

    def lerp(
        self,
        other: Point,
        t: Real,
    ) -> Point:
        t_value = _finite_real(
            t,
            name="t",
            path="geometry/point",
        )

        return Point(
            lerp_scalar(
                self.x,
                other.x,
                t_value,
            ),
            lerp_scalar(
                self.y,
                other.y,
                t_value,
            ),
        )

    def transformed(
        self,
        transform: AffineTransform,
    ) -> Point:
        return transform.apply_point(
            self
        )


ORIGIN: Final[Point] = Point(
    0.0,
    0.0,
)

ZERO_VECTOR: Final[Vector] = Vector(
    0.0,
    0.0,
)


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        values = {
            "min_x": _finite_real(
                self.min_x,
                name="bounds.min_x",
                path="geometry/bounds",
            ),
            "min_y": _finite_real(
                self.min_y,
                name="bounds.min_y",
                path="geometry/bounds",
            ),
            "max_x": _finite_real(
                self.max_x,
                name="bounds.max_x",
                path="geometry/bounds",
            ),
            "max_y": _finite_real(
                self.max_y,
                name="bounds.max_y",
                path="geometry/bounds",
            ),
        }

        if values["min_x"] > values["max_x"]:
            raise BoundsError(
                "bounds min_x exceeds max_x",
                path="geometry/bounds",
            )

        if values["min_y"] > values["max_y"]:
            raise BoundsError(
                "bounds min_y exceeds max_y",
                path="geometry/bounds",
            )

        for name, value in values.items():
            object.__setattr__(
                self,
                name,
                value,
            )

    @classmethod
    def from_point(
        cls,
        point: Point,
    ) -> Self:
        return cls(
            point.x,
            point.y,
            point.x,
            point.y,
        )

    @classmethod
    def from_points(
        cls,
        points: Iterable[Point],
    ) -> Self:
        iterator = iter(
            points
        )

        try:
            first = next(
                iterator
            )
        except StopIteration as exc:
            raise BoundsError(
                "cannot construct bounds from an empty point sequence",
                path="geometry/bounds",
            ) from exc

        min_x = max_x = first.x
        min_y = max_y = first.y

        for point in iterator:
            min_x = min(
                min_x,
                point.x,
            )
            min_y = min(
                min_y,
                point.y,
            )
            max_x = max(
                max_x,
                point.x,
            )
            max_y = max(
                max_y,
                point.y,
            )

        return cls(
            min_x,
            min_y,
            max_x,
            max_y,
        )

    @property
    def width(self) -> float:
        return (
            self.max_x
            - self.min_x
        )

    @property
    def height(self) -> float:
        return (
            self.max_y
            - self.min_y
        )

    @property
    def center(self) -> Point:
        return Point(
            (
                self.min_x
                + self.max_x
            )
            / 2.0,
            (
                self.min_y
                + self.max_y
            )
            / 2.0,
        )

    @property
    def top_left(self) -> Point:
        return Point(
            self.min_x,
            self.min_y,
        )

    @property
    def top_right(self) -> Point:
        return Point(
            self.max_x,
            self.min_y,
        )

    @property
    def bottom_left(self) -> Point:
        return Point(
            self.min_x,
            self.max_y,
        )

    @property
    def bottom_right(self) -> Point:
        return Point(
            self.max_x,
            self.max_y,
        )

    @property
    def corners(
        self,
    ) -> tuple[
        Point,
        Point,
        Point,
        Point,
    ]:
        return (
            self.top_left,
            self.top_right,
            self.bottom_right,
            self.bottom_left,
        )

    def contains_point(
        self,
        point: Point,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> bool:
        return (
            self.min_x - tolerance.epsilon
            <= point.x
            <= self.max_x + tolerance.epsilon
            and
            self.min_y - tolerance.epsilon
            <= point.y
            <= self.max_y + tolerance.epsilon
        )

    def union(
        self,
        other: Bounds,
    ) -> Bounds:
        return Bounds(
            min(
                self.min_x,
                other.min_x,
            ),
            min(
                self.min_y,
                other.min_y,
            ),
            max(
                self.max_x,
                other.max_x,
            ),
            max(
                self.max_y,
                other.max_y,
            ),
        )

    def intersection(
        self,
        other: Bounds,
    ) -> Bounds | None:
        min_x = max(
            self.min_x,
            other.min_x,
        )
        min_y = max(
            self.min_y,
            other.min_y,
        )
        max_x = min(
            self.max_x,
            other.max_x,
        )
        max_y = min(
            self.max_y,
            other.max_y,
        )

        if (
            min_x > max_x
            or min_y > max_y
        ):
            return None

        return Bounds(
            min_x,
            min_y,
            max_x,
            max_y,
        )

    def expanded(
        self,
        amount_x: Real,
        amount_y: Real | None = None,
    ) -> Bounds:
        x = _positive_finite(
            amount_x,
            name="amount_x",
            path="geometry/bounds",
            allow_zero=True,
        )

        y = (
            x
            if amount_y is None
            else _positive_finite(
                amount_y,
                name="amount_y",
                path="geometry/bounds",
                allow_zero=True,
            )
        )

        return Bounds(
            self.min_x - x,
            self.min_y - y,
            self.max_x + x,
            self.max_y + y,
        )

    def translated(
        self,
        vector: Vector,
    ) -> Bounds:
        return Bounds(
            self.min_x + vector.x,
            self.min_y + vector.y,
            self.max_x + vector.x,
            self.max_y + vector.y,
        )

    def transformed(
        self,
        transform: AffineTransform,
    ) -> Bounds:
        return transform.apply_bounds(
            self
        )


def union_bounds(
    bounds: Iterable[Bounds],
) -> Bounds | None:
    result: Bounds | None = None

    for item in bounds:
        result = (
            item
            if result is None
            else result.union(item)
        )

    return result


# ---------------------------------------------------------------------------
# Affine transform algebra
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AffineTransform:
    """
    Standard SVG-compatible affine matrix.

    Matrix representation::

        | a c e |
        | b d f |
        | 0 0 1 |

    Point mapping::

        x' = a*x + c*y + e
        y' = b*x + d*y + f

    ``left @ right`` means matrix multiplication in mathematical order:
    ``right`` is applied first, then ``left``.

    For code that wants explicit visual operation order, use ``then()``.
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
        ):
            object.__setattr__(
                self,
                name,
                _finite_real(
                    getattr(
                        self,
                        name,
                    ),
                    name=f"transform.{name}",
                    path="geometry/transform",
                ),
            )

    @classmethod
    def identity(cls) -> Self:
        return cls()

    @classmethod
    def translate(
        cls,
        tx: Real,
        ty: Real = 0.0,
    ) -> Self:
        return cls(
            e=_finite_real(
                tx,
                name="translate.tx",
                path="geometry/transform",
            ),
            f=_finite_real(
                ty,
                name="translate.ty",
                path="geometry/transform",
            ),
        )

    @classmethod
    def scale(
        cls,
        sx: Real,
        sy: Real | None = None,
    ) -> Self:
        x = _finite_real(
            sx,
            name="scale.sx",
            path="geometry/transform",
        )

        y = (
            x
            if sy is None
            else _finite_real(
                sy,
                name="scale.sy",
                path="geometry/transform",
            )
        )

        return cls(
            a=x,
            d=y,
        )

    @classmethod
    def rotate(
        cls,
        degrees: Real,
    ) -> Self:
        angle = math.radians(
            _finite_real(
                degrees,
                name="rotation.degrees",
                path="geometry/transform",
            )
        )

        cosine = math.cos(
            angle
        )
        sine = math.sin(
            angle
        )

        return cls(
            a=cosine,
            b=sine,
            c=-sine,
            d=cosine,
        )

    @classmethod
    def rotate_radians(
        cls,
        radians: Real,
    ) -> Self:
        angle = _finite_real(
            radians,
            name="rotation.radians",
            path="geometry/transform",
        )

        cosine = math.cos(
            angle
        )
        sine = math.sin(
            angle
        )

        return cls(
            a=cosine,
            b=sine,
            c=-sine,
            d=cosine,
        )

    @classmethod
    def rotate_about(
        cls,
        degrees: Real,
        center: Point,
    ) -> Self:
        return (
            cls.translate(
                center.x,
                center.y,
            )
            @ cls.rotate(
                degrees
            )
            @ cls.translate(
                -center.x,
                -center.y,
            )
        )

    @classmethod
    def skew_x(
        cls,
        degrees: Real,
    ) -> Self:
        angle = math.radians(
            _finite_real(
                degrees,
                name="skew_x.degrees",
                path="geometry/transform",
            )
        )

        return cls(
            c=math.tan(
                angle
            ),
        )

    @classmethod
    def skew_y(
        cls,
        degrees: Real,
    ) -> Self:
        angle = math.radians(
            _finite_real(
                degrees,
                name="skew_y.degrees",
                path="geometry/transform",
            )
        )

        return cls(
            b=math.tan(
                angle
            ),
        )

    @property
    def determinant(self) -> float:
        return (
            self.a * self.d
            - self.b * self.c
        )

    def is_identity(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> bool:
        identity = AffineTransform.identity()

        return all(
            tolerance.close(
                getattr(
                    self,
                    name,
                ),
                getattr(
                    identity,
                    name,
                ),
            )
            for name in (
                "a",
                "b",
                "c",
                "d",
                "e",
                "f",
            )
        )

    def is_singular(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> bool:
        return (
            abs(
                self.determinant
            )
            <= tolerance.epsilon
        )

    def inverse(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> AffineTransform:
        determinant = self.determinant

        if abs(
            determinant
        ) <= tolerance.epsilon:
            raise SingularTransformError(
                "cannot invert a singular affine transform",
                path="geometry/transform",
                context={
                    "determinant": determinant,
                },
            )

        reciprocal = (
            1.0
            / determinant
        )

        return AffineTransform(
            a=self.d * reciprocal,
            b=-self.b * reciprocal,
            c=-self.c * reciprocal,
            d=self.a * reciprocal,
            e=(
                self.c * self.f
                - self.d * self.e
            )
            * reciprocal,
            f=(
                self.b * self.e
                - self.a * self.f
            )
            * reciprocal,
        )

    def __matmul__(
        self,
        other: AffineTransform,
    ) -> AffineTransform:
        if not isinstance(
            other,
            AffineTransform,
        ):
            return NotImplemented

        return AffineTransform(
            a=(
                self.a * other.a
                + self.c * other.b
            ),
            b=(
                self.b * other.a
                + self.d * other.b
            ),
            c=(
                self.a * other.c
                + self.c * other.d
            ),
            d=(
                self.b * other.c
                + self.d * other.d
            ),
            e=(
                self.a * other.e
                + self.c * other.f
                + self.e
            ),
            f=(
                self.b * other.e
                + self.d * other.f
                + self.f
            ),
        )

    def then(
        self,
        next_transform: AffineTransform,
    ) -> AffineTransform:
        """
        Compose in explicit operation order.

        ``a.then(b)`` means apply ``a`` first, then apply ``b``.
        """

        return (
            next_transform
            @ self
        )

    def apply_point(
        self,
        point: Point,
    ) -> Point:
        return Point(
            (
                self.a * point.x
                + self.c * point.y
                + self.e
            ),
            (
                self.b * point.x
                + self.d * point.y
                + self.f
            ),
        )

    def apply_vector(
        self,
        vector: Vector,
    ) -> Vector:
        return Vector(
            (
                self.a * vector.x
                + self.c * vector.y
            ),
            (
                self.b * vector.x
                + self.d * vector.y
            ),
        )

    def apply_bounds(
        self,
        bounds: Bounds,
    ) -> Bounds:
        return Bounds.from_points(
            self.apply_point(
                point
            )
            for point in bounds.corners
        )

    def positive_uniform_similarity(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> tuple[
        float,
        float,
    ] | None:
        """
        Return ``(scale, rotation_degrees)`` when the linear transform is a
        positive-orientation uniform scale+rotation.

        Translation is irrelevant.

        Reflections, nonuniform scales, and skews return ``None`` because
        preserving SVG arc endpoint parameters under those transforms
        requires a more general ellipse decomposition.
        """

        first = Vector(
            self.a,
            self.b,
        )
        second = Vector(
            self.c,
            self.d,
        )

        first_length = (
            first.magnitude
        )
        second_length = (
            second.magnitude
        )

        if (
            first_length
            <= tolerance.epsilon
            or second_length
            <= tolerance.epsilon
        ):
            return None

        if not tolerance.close(
            first_length,
            second_length,
        ):
            return None

        if (
            abs(
                first.dot(second)
            )
            > (
                tolerance.epsilon
                * first_length
                * second_length
            )
        ):
            return None

        if self.determinant <= 0.0:
            return None

        rotation = math.degrees(
            math.atan2(
                self.b,
                self.a,
            )
        )

        return (
            (
                first_length
                + second_length
            )
            / 2.0,
            normalize_degrees(
                rotation
            ),
        )


IDENTITY_TRANSFORM: Final[
    AffineTransform
] = AffineTransform.identity()


# ---------------------------------------------------------------------------
# Numeric integration
# ---------------------------------------------------------------------------


def _simpson(
    function: Callable[[float], float],
    start: float,
    end: float,
) -> float:
    midpoint = (
        start
        + end
    ) / 2.0

    return (
        (end - start)
        / 6.0
        * (
            function(start)
            + 4.0
            * function(midpoint)
            + function(end)
        )
    )


def _adaptive_simpson(
    function: Callable[[float], float],
    start: float,
    end: float,
    tolerance: float,
    *,
    max_depth: int,
) -> float:
    whole = _simpson(
        function,
        start,
        end,
    )

    def recurse(
        left: float,
        right: float,
        expected: float,
        local_tolerance: float,
        depth: int,
    ) -> float:
        midpoint = (
            left
            + right
        ) / 2.0

        left_value = _simpson(
            function,
            left,
            midpoint,
        )

        right_value = _simpson(
            function,
            midpoint,
            right,
        )

        combined = (
            left_value
            + right_value
        )

        error = (
            combined
            - expected
        )

        if (
            depth <= 0
            or abs(error)
            <= 15.0
            * local_tolerance
        ):
            return (
                combined
                + error / 15.0
            )

        return (
            recurse(
                left,
                midpoint,
                left_value,
                local_tolerance / 2.0,
                depth - 1,
            )
            + recurse(
                midpoint,
                right,
                right_value,
                local_tolerance / 2.0,
                depth - 1,
            )
        )

    return recurse(
        start,
        end,
        whole,
        tolerance,
        max_depth,
    )


# ---------------------------------------------------------------------------
# Polynomial roots
# ---------------------------------------------------------------------------


def _quadratic_roots(
    a: float,
    b: float,
    c: float,
    *,
    tolerance: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> tuple[float, ...]:
    """
    Stable real roots for ``a*x² + b*x + c = 0``.
    """

    if abs(a) <= tolerance.epsilon:
        if abs(b) <= tolerance.epsilon:
            return ()

        return (
            -c / b,
        )

    discriminant = (
        b * b
        - 4.0 * a * c
    )

    if (
        discriminant
        < -tolerance.epsilon
    ):
        return ()

    if abs(
        discriminant
    ) <= tolerance.epsilon:
        return (
            -b
            / (
                2.0 * a
            ),
        )

    root = math.sqrt(
        max(
            discriminant,
            0.0,
        )
    )

    q = (
        -0.5
        * (
            b
            + math.copysign(
                root,
                b,
            )
        )
    )

    if abs(q) <= tolerance.epsilon:
        return (
            (
                -b + root
            )
            / (
                2.0 * a
            ),
            (
                -b - root
            )
            / (
                2.0 * a
            ),
        )

    first = (
        q / a
    )
    second = (
        c / q
    )

    if tolerance.close(
        first,
        second,
    ):
        return (
            first,
        )

    return tuple(
        sorted(
            (
                first,
                second,
            )
        )
    )


def _roots_inside_unit_interval(
    roots: Iterable[float],
    *,
    tolerance: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> tuple[float, ...]:
    accepted: list[float] = []

    for root in roots:
        if (
            root
            > tolerance.epsilon
            and root
            < (
                1.0
                - tolerance.epsilon
            )
        ):
            if not any(
                tolerance.close(
                    root,
                    existing,
                )
                for existing in accepted
            ):
                accepted.append(
                    root
                )

    return tuple(
        sorted(
            accepted
        )
    )


# ---------------------------------------------------------------------------
# Segment protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Segment(Protocol):
    start: Point
    end: Point

    def point_at(
        self,
        t: Real,
    ) -> Point:
        ...

    def derivative_at(
        self,
        t: Real,
    ) -> Vector:
        ...

    def tangent_at(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        ...

    def bounds(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Bounds:
        ...

    def length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        ...

    def length_to(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        ...


def _unit_parameter(
    value: Real,
    *,
    name: str = "t",
) -> float:
    result = _finite_real(
        value,
        name=name,
        path="geometry/segment",
    )

    if not (
        0.0
        <= result
        <= 1.0
    ):
        raise InvalidGeometryError(
            f"{name} must lie within [0, 1]",
            path="geometry/segment",
            context={
                "value": result,
            },
        )

    return result


# ---------------------------------------------------------------------------
# Line segment
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineSegment:
    start: Point
    end: Point

    def point_at(
        self,
        t: Real,
    ) -> Point:
        parameter = _unit_parameter(
            t
        )

        return self.start.lerp(
            self.end,
            parameter,
        )

    def derivative_at(
        self,
        t: Real,
    ) -> Vector:
        _unit_parameter(
            t
        )

        return (
            self.end
            - self.start
        )

    def tangent_at(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        return self.derivative_at(
            t
        ).normalized(
            tolerance=tolerance
        )

    def bounds(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Bounds:
        del tolerance

        return Bounds.from_points(
            (
                self.start,
                self.end,
            )
        )

    def length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        del tolerance

        return self.start.distance_to(
            self.end
        )

    def length_to(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        del tolerance

        return (
            self.length()
            * _unit_parameter(t)
        )

    def subdivide(
        self,
        t: Real = 0.5,
    ) -> tuple[
        LineSegment,
        LineSegment,
    ]:
        parameter = _unit_parameter(
            t
        )

        midpoint = self.point_at(
            parameter
        )

        return (
            LineSegment(
                self.start,
                midpoint,
            ),
            LineSegment(
                midpoint,
                self.end,
            ),
        )


# ---------------------------------------------------------------------------
# Quadratic Bézier
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuadraticBezierSegment:
    start: Point
    control: Point
    end: Point

    def point_at(
        self,
        t: Real,
    ) -> Point:
        parameter = _unit_parameter(
            t
        )

        inverse = (
            1.0
            - parameter
        )

        return Point(
            (
                inverse
                * inverse
                * self.start.x
                + 2.0
                * inverse
                * parameter
                * self.control.x
                + parameter
                * parameter
                * self.end.x
            ),
            (
                inverse
                * inverse
                * self.start.y
                + 2.0
                * inverse
                * parameter
                * self.control.y
                + parameter
                * parameter
                * self.end.y
            ),
        )

    def derivative_at(
        self,
        t: Real,
    ) -> Vector:
        parameter = _unit_parameter(
            t
        )

        inverse = (
            1.0
            - parameter
        )

        return Vector(
            (
                2.0
                * inverse
                * (
                    self.control.x
                    - self.start.x
                )
                + 2.0
                * parameter
                * (
                    self.end.x
                    - self.control.x
                )
            ),
            (
                2.0
                * inverse
                * (
                    self.control.y
                    - self.start.y
                )
                + 2.0
                * parameter
                * (
                    self.end.y
                    - self.control.y
                )
            ),
        )

    def tangent_at(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        return self.derivative_at(
            t
        ).normalized(
            tolerance=tolerance
        )

    @staticmethod
    def _axis_extremum(
        start: float,
        control: float,
        end: float,
        *,
        tolerance: TolerancePolicy,
    ) -> tuple[float, ...]:
        denominator = (
            start
            - 2.0 * control
            + end
        )

        if abs(
            denominator
        ) <= tolerance.epsilon:
            return ()

        root = (
            start
            - control
        ) / denominator

        return _roots_inside_unit_interval(
            (
                root,
            ),
            tolerance=tolerance,
        )

    def extrema_parameters(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> tuple[float, ...]:
        roots = set(
            self._axis_extremum(
                self.start.x,
                self.control.x,
                self.end.x,
                tolerance=tolerance,
            )
        )

        roots.update(
            self._axis_extremum(
                self.start.y,
                self.control.y,
                self.end.y,
                tolerance=tolerance,
            )
        )

        return tuple(
            sorted(
                roots
            )
        )

    def bounds(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Bounds:
        points = [
            self.start,
            self.end,
        ]

        points.extend(
            self.point_at(parameter)
            for parameter
            in self.extrema_parameters(
                tolerance=tolerance
            )
        )

        return Bounds.from_points(
            points
        )

    def subdivide(
        self,
        t: Real = 0.5,
    ) -> tuple[
        QuadraticBezierSegment,
        QuadraticBezierSegment,
    ]:
        parameter = _unit_parameter(
            t
        )

        first = self.start.lerp(
            self.control,
            parameter,
        )

        second = self.control.lerp(
            self.end,
            parameter,
        )

        midpoint = first.lerp(
            second,
            parameter,
        )

        return (
            QuadraticBezierSegment(
                self.start,
                first,
                midpoint,
            ),
            QuadraticBezierSegment(
                midpoint,
                second,
                self.end,
            ),
        )

    def _speed(
        self,
        t: float,
    ) -> float:
        return self.derivative_at(
            t
        ).magnitude

    def length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        return _adaptive_simpson(
            self._speed,
            0.0,
            1.0,
            tolerance.length_tolerance,
            max_depth=(
                tolerance.max_integration_depth
            ),
        )

    def length_to(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        parameter = _unit_parameter(
            t
        )

        if parameter == 0.0:
            return 0.0

        if parameter == 1.0:
            return self.length(
                tolerance=tolerance
            )

        return _adaptive_simpson(
            self._speed,
            0.0,
            parameter,
            tolerance.length_tolerance,
            max_depth=(
                tolerance.max_integration_depth
            ),
        )


# ---------------------------------------------------------------------------
# Cubic Bézier
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CubicBezierSegment:
    start: Point
    control1: Point
    control2: Point
    end: Point

    def point_at(
        self,
        t: Real,
    ) -> Point:
        parameter = _unit_parameter(
            t
        )

        inverse = (
            1.0
            - parameter
        )

        inverse2 = (
            inverse
            * inverse
        )

        parameter2 = (
            parameter
            * parameter
        )

        return Point(
            (
                inverse2
                * inverse
                * self.start.x
                + 3.0
                * inverse2
                * parameter
                * self.control1.x
                + 3.0
                * inverse
                * parameter2
                * self.control2.x
                + parameter2
                * parameter
                * self.end.x
            ),
            (
                inverse2
                * inverse
                * self.start.y
                + 3.0
                * inverse2
                * parameter
                * self.control1.y
                + 3.0
                * inverse
                * parameter2
                * self.control2.y
                + parameter2
                * parameter
                * self.end.y
            ),
        )

    def derivative_at(
        self,
        t: Real,
    ) -> Vector:
        parameter = _unit_parameter(
            t
        )

        inverse = (
            1.0
            - parameter
        )

        return Vector(
            (
                3.0
                * inverse
                * inverse
                * (
                    self.control1.x
                    - self.start.x
                )
                + 6.0
                * inverse
                * parameter
                * (
                    self.control2.x
                    - self.control1.x
                )
                + 3.0
                * parameter
                * parameter
                * (
                    self.end.x
                    - self.control2.x
                )
            ),
            (
                3.0
                * inverse
                * inverse
                * (
                    self.control1.y
                    - self.start.y
                )
                + 6.0
                * inverse
                * parameter
                * (
                    self.control2.y
                    - self.control1.y
                )
                + 3.0
                * parameter
                * parameter
                * (
                    self.end.y
                    - self.control2.y
                )
            ),
        )

    def tangent_at(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        derivative = self.derivative_at(
            t
        )

        if (
            derivative.magnitude
            > tolerance.epsilon
        ):
            return derivative.normalized(
                tolerance=tolerance
            )

        parameter = _unit_parameter(
            t
        )

        probes = (
            max(
                0.0,
                parameter
                - 1.0e-7,
            ),
            min(
                1.0,
                parameter
                + 1.0e-7,
            ),
        )

        for probe in probes:
            candidate = self.derivative_at(
                probe
            )

            if (
                candidate.magnitude
                > tolerance.epsilon
            ):
                return candidate.normalized(
                    tolerance=tolerance
                )

        raise DegenerateGeometryError(
            "cubic Bézier tangent is undefined at the requested parameter",
            path="geometry/cubic",
        )

    @staticmethod
    def _axis_extrema(
        start: float,
        control1: float,
        control2: float,
        end: float,
        *,
        tolerance: TolerancePolicy,
    ) -> tuple[float, ...]:
        a = (
            -start
            + 3.0 * control1
            - 3.0 * control2
            + end
        )

        b = (
            3.0 * start
            - 6.0 * control1
            + 3.0 * control2
        )

        c = (
            -3.0 * start
            + 3.0 * control1
        )

        roots = _quadratic_roots(
            3.0 * a,
            2.0 * b,
            c,
            tolerance=tolerance,
        )

        return _roots_inside_unit_interval(
            roots,
            tolerance=tolerance,
        )

    def extrema_parameters(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> tuple[float, ...]:
        roots = set(
            self._axis_extrema(
                self.start.x,
                self.control1.x,
                self.control2.x,
                self.end.x,
                tolerance=tolerance,
            )
        )

        roots.update(
            self._axis_extrema(
                self.start.y,
                self.control1.y,
                self.control2.y,
                self.end.y,
                tolerance=tolerance,
            )
        )

        return tuple(
            sorted(
                roots
            )
        )

    def bounds(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Bounds:
        points = [
            self.start,
            self.end,
        ]

        points.extend(
            self.point_at(parameter)
            for parameter
            in self.extrema_parameters(
                tolerance=tolerance
            )
        )

        return Bounds.from_points(
            points
        )

    def subdivide(
        self,
        t: Real = 0.5,
    ) -> tuple[
        CubicBezierSegment,
        CubicBezierSegment,
    ]:
        parameter = _unit_parameter(
            t
        )

        p01 = self.start.lerp(
            self.control1,
            parameter,
        )

        p12 = self.control1.lerp(
            self.control2,
            parameter,
        )

        p23 = self.control2.lerp(
            self.end,
            parameter,
        )

        p012 = p01.lerp(
            p12,
            parameter,
        )

        p123 = p12.lerp(
            p23,
            parameter,
        )

        midpoint = p012.lerp(
            p123,
            parameter,
        )

        return (
            CubicBezierSegment(
                self.start,
                p01,
                p012,
                midpoint,
            ),
            CubicBezierSegment(
                midpoint,
                p123,
                p23,
                self.end,
            ),
        )

    def _speed(
        self,
        t: float,
    ) -> float:
        return self.derivative_at(
            t
        ).magnitude

    def length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        return _adaptive_simpson(
            self._speed,
            0.0,
            1.0,
            tolerance.length_tolerance,
            max_depth=(
                tolerance.max_integration_depth
            ),
        )

    def length_to(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        parameter = _unit_parameter(
            t
        )

        if parameter == 0.0:
            return 0.0

        if parameter == 1.0:
            return self.length(
                tolerance=tolerance
            )

        return _adaptive_simpson(
            self._speed,
            0.0,
            parameter,
            tolerance.length_tolerance,
            max_depth=(
                tolerance.max_integration_depth
            ),
        )


# ---------------------------------------------------------------------------
# Elliptical arc center representation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArcCenterParameters:
    center: Point
    rx: float
    ry: float
    rotation_radians: float
    start_angle: float
    delta_angle: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rx",
            _positive_finite(
                self.rx,
                name="arc.rx",
                path="geometry/arc",
            ),
        )

        object.__setattr__(
            self,
            "ry",
            _positive_finite(
                self.ry,
                name="arc.ry",
                path="geometry/arc",
            ),
        )

        for name in (
            "rotation_radians",
            "start_angle",
            "delta_angle",
        ):
            object.__setattr__(
                self,
                name,
                _finite_real(
                    getattr(
                        self,
                        name,
                    ),
                    name=f"arc.{name}",
                    path="geometry/arc",
                ),
            )

    @property
    def end_angle(self) -> float:
        return (
            self.start_angle
            + self.delta_angle
        )


def _vector_angle(
    first: Vector,
    second: Vector,
    *,
    tolerance: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> float:
    first_length = (
        first.magnitude
    )
    second_length = (
        second.magnitude
    )

    if (
        first_length
        <= tolerance.epsilon
        or second_length
        <= tolerance.epsilon
    ):
        raise ArcGeometryError(
            "cannot calculate angle involving a zero-length vector",
            path="geometry/arc",
        )

    cosine = clamp(
        first.dot(second)
        / (
            first_length
            * second_length
        ),
        -1.0,
        1.0,
    )

    angle = math.acos(
        cosine
    )

    if (
        first.cross(second)
        < 0.0
    ):
        angle = -angle

    return angle


def _angle_on_sweep(
    angle: float,
    start: float,
    delta: float,
    *,
    tolerance: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> bool:
    if delta >= 0.0:
        travel = normalize_angle_radians(
            angle - start
        )

        return (
            travel
            <= (
                delta
                + tolerance.angle_epsilon
            )
        )

    travel = normalize_angle_radians(
        start - angle
    )

    return (
        travel
        <= (
            -delta
            + tolerance.angle_epsilon
        )
    )


def _arc_point_at_angle(
    parameters: ArcCenterParameters,
    angle: float,
) -> Point:
    cosine_phi = math.cos(
        parameters.rotation_radians
    )
    sine_phi = math.sin(
        parameters.rotation_radians
    )

    cosine_theta = math.cos(
        angle
    )
    sine_theta = math.sin(
        angle
    )

    return Point(
        (
            parameters.center.x
            + parameters.rx
            * cosine_phi
            * cosine_theta
            - parameters.ry
            * sine_phi
            * sine_theta
        ),
        (
            parameters.center.y
            + parameters.rx
            * sine_phi
            * cosine_theta
            + parameters.ry
            * cosine_phi
            * sine_theta
        ),
    )


def _arc_derivative_angle(
    parameters: ArcCenterParameters,
    angle: float,
) -> Vector:
    cosine_phi = math.cos(
        parameters.rotation_radians
    )
    sine_phi = math.sin(
        parameters.rotation_radians
    )

    cosine_theta = math.cos(
        angle
    )
    sine_theta = math.sin(
        angle
    )

    return Vector(
        (
            -parameters.rx
            * cosine_phi
            * sine_theta
            - parameters.ry
            * sine_phi
            * cosine_theta
        ),
        (
            -parameters.rx
            * sine_phi
            * sine_theta
            + parameters.ry
            * cosine_phi
            * cosine_theta
        ),
    )


# ---------------------------------------------------------------------------
# Elliptical arc segment
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EllipticalArcSegment:
    start: Point
    rx: float
    ry: float
    x_axis_rotation: float
    large_arc: bool
    sweep: bool
    end: Point

    def __post_init__(self) -> None:
        rx = _positive_finite(
            self.rx,
            name="arc.rx",
            path="geometry/arc",
            allow_zero=True,
        )

        ry = _positive_finite(
            self.ry,
            name="arc.ry",
            path="geometry/arc",
            allow_zero=True,
        )

        rotation = normalize_degrees(
            _finite_real(
                self.x_axis_rotation,
                name="arc.x_axis_rotation",
                path="geometry/arc",
            )
        )

        if not isinstance(
            self.large_arc,
            bool,
        ):
            raise ArcGeometryError(
                "arc large_arc flag must be boolean",
                path="geometry/arc",
            )

        if not isinstance(
            self.sweep,
            bool,
        ):
            raise ArcGeometryError(
                "arc sweep flag must be boolean",
                path="geometry/arc",
            )

        object.__setattr__(
            self,
            "rx",
            rx,
        )
        object.__setattr__(
            self,
            "ry",
            ry,
        )
        object.__setattr__(
            self,
            "x_axis_rotation",
            rotation,
        )

    def is_zero_length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> bool:
        return (
            self.start.distance_to(
                self.end
            )
            <= tolerance.epsilon
        )

    def is_line_like(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> bool:
        return (
            self.rx
            <= tolerance.epsilon
            or self.ry
            <= tolerance.epsilon
        )

    def center_parameters(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> ArcCenterParameters:
        if self.is_zero_length(
            tolerance=tolerance
        ):
            raise DegenerateGeometryError(
                "zero-length elliptical arc has no unique center form",
                path="geometry/arc",
            )

        if self.is_line_like(
            tolerance=tolerance
        ):
            raise DegenerateGeometryError(
                "zero-radius elliptical arc is line-like and has no ellipse center form",
                path="geometry/arc",
            )

        rx = abs(
            self.rx
        )
        ry = abs(
            self.ry
        )

        phi = math.radians(
            self.x_axis_rotation
        )

        cosine_phi = math.cos(
            phi
        )
        sine_phi = math.sin(
            phi
        )

        half_dx = (
            self.start.x
            - self.end.x
        ) / 2.0

        half_dy = (
            self.start.y
            - self.end.y
        ) / 2.0

        x1_prime = (
            cosine_phi
            * half_dx
            + sine_phi
            * half_dy
        )

        y1_prime = (
            -sine_phi
            * half_dx
            + cosine_phi
            * half_dy
        )

        radii_scale = (
            x1_prime
            * x1_prime
            / (
                rx * rx
            )
            + y1_prime
            * y1_prime
            / (
                ry * ry
            )
        )

        if radii_scale > 1.0:
            scale = math.sqrt(
                radii_scale
            )

            rx *= scale
            ry *= scale

        numerator = (
            rx
            * rx
            * ry
            * ry
            - rx
            * rx
            * y1_prime
            * y1_prime
            - ry
            * ry
            * x1_prime
            * x1_prime
        )

        denominator = (
            rx
            * rx
            * y1_prime
            * y1_prime
            + ry
            * ry
            * x1_prime
            * x1_prime
        )

        if denominator <= tolerance.epsilon:
            raise ArcGeometryError(
                "elliptical arc center conversion encountered a degenerate denominator",
                path="geometry/arc",
            )

        ratio = max(
            0.0,
            numerator
            / denominator,
        )

        coefficient = math.sqrt(
            ratio
        )

        if (
            self.large_arc
            == self.sweep
        ):
            coefficient = -coefficient

        cx_prime = (
            coefficient
            * (
                rx
                * y1_prime
                / ry
            )
        )

        cy_prime = (
            coefficient
            * (
                -ry
                * x1_prime
                / rx
            )
        )

        midpoint_x = (
            self.start.x
            + self.end.x
        ) / 2.0

        midpoint_y = (
            self.start.y
            + self.end.y
        ) / 2.0

        center = Point(
            (
                cosine_phi
                * cx_prime
                - sine_phi
                * cy_prime
                + midpoint_x
            ),
            (
                sine_phi
                * cx_prime
                + cosine_phi
                * cy_prime
                + midpoint_y
            ),
        )

        start_vector = Vector(
            (
                x1_prime
                - cx_prime
            )
            / rx,
            (
                y1_prime
                - cy_prime
            )
            / ry,
        )

        end_vector = Vector(
            (
                -x1_prime
                - cx_prime
            )
            / rx,
            (
                -y1_prime
                - cy_prime
            )
            / ry,
        )

        start_angle = _vector_angle(
            Vector(
                1.0,
                0.0,
            ),
            start_vector,
            tolerance=tolerance,
        )

        delta_angle = _vector_angle(
            start_vector,
            end_vector,
            tolerance=tolerance,
        )

        if (
            not self.sweep
            and delta_angle > 0.0
        ):
            delta_angle -= TAU
        elif (
            self.sweep
            and delta_angle < 0.0
        ):
            delta_angle += TAU

        return ArcCenterParameters(
            center=center,
            rx=rx,
            ry=ry,
            rotation_radians=phi,
            start_angle=start_angle,
            delta_angle=delta_angle,
        )

    def point_at(
        self,
        t: Real,
    ) -> Point:
        """
        Evaluate the elliptical arc at normalized parameter ``t``.

        The canonical semantic endpoints are returned directly at exactly
        ``t == 0`` and ``t == 1``.

        This is intentional. Endpoint-form SVG arcs are converted to a
        derived center representation for intermediate evaluation. That
        conversion necessarily passes through floating-point trigonometry
        and can reconstruct an endpoint with tiny numerical drift.

        Canonical endpoints are authoritative scene geometry, so exact
        endpoint queries must preserve them byte-for-byte at the numeric
        model level rather than replacing them with reconstructed values.
        """

        parameter = _unit_parameter(
            t
        )

        if parameter == 0.0:
            return self.start

        if parameter == 1.0:
            return self.end

        if self.is_zero_length():
            return self.start

        if self.is_line_like():
            return self.start.lerp(
                self.end,
                parameter,
            )

        center = self.center_parameters()

        angle = (
            center.start_angle
            + center.delta_angle
            * parameter
        )

        return _arc_point_at_angle(
            center,
            angle,
        )

    def derivative_at(
        self,
        t: Real,
    ) -> Vector:
        parameter = _unit_parameter(
            t
        )

        if self.is_zero_length():
            return ZERO_VECTOR

        if self.is_line_like():
            return (
                self.end
                - self.start
            )

        center = self.center_parameters()

        angle = (
            center.start_angle
            + center.delta_angle
            * parameter
        )

        return (
            _arc_derivative_angle(
                center,
                angle,
            )
            * center.delta_angle
        )

    def tangent_at(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        derivative = self.derivative_at(
            t
        )

        return derivative.normalized(
            tolerance=tolerance
        )

    def extrema_angles(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> tuple[float, ...]:
        if (
            self.is_zero_length(
                tolerance=tolerance
            )
            or self.is_line_like(
                tolerance=tolerance
            )
        ):
            return ()

        center = self.center_parameters(
            tolerance=tolerance
        )

        phi = (
            center.rotation_radians
        )

        x_base = math.atan2(
            center.ry
            * math.sin(phi),
            -center.rx
            * math.cos(phi),
        )

        y_base = math.atan2(
            -center.ry
            * math.cos(phi),
            -center.rx
            * math.sin(phi),
        )

        candidates = (
            x_base,
            x_base + PI,
            y_base,
            y_base + PI,
        )

        accepted = [
            angle
            for angle in candidates
            if _angle_on_sweep(
                angle,
                center.start_angle,
                center.delta_angle,
                tolerance=tolerance,
            )
        ]

        normalized: list[float] = []

        for angle in accepted:
            value = normalize_angle_radians(
                angle
            )

            if not any(
                abs(
                    normalize_angle_radians(
                        value - existing
                    )
                )
                <= tolerance.angle_epsilon
                for existing in normalized
            ):
                normalized.append(
                    value
                )

        return tuple(
            sorted(
                normalized
            )
        )

    def bounds(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Bounds:
        if self.is_zero_length(
            tolerance=tolerance
        ):
            return Bounds.from_point(
                self.start
            )

        if self.is_line_like(
            tolerance=tolerance
        ):
            return Bounds.from_points(
                (
                    self.start,
                    self.end,
                )
            )

        center = self.center_parameters(
            tolerance=tolerance
        )

        points = [
            self.start,
            self.end,
        ]

        points.extend(
            _arc_point_at_angle(
                center,
                angle,
            )
            for angle
            in self.extrema_angles(
                tolerance=tolerance
            )
        )

        return Bounds.from_points(
            points
        )

    def _speed(
        self,
        t: float,
    ) -> float:
        return self.derivative_at(
            t
        ).magnitude

    def length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        if self.is_zero_length(
            tolerance=tolerance
        ):
            return 0.0

        if self.is_line_like(
            tolerance=tolerance
        ):
            return self.start.distance_to(
                self.end
            )

        return _adaptive_simpson(
            self._speed,
            0.0,
            1.0,
            tolerance.length_tolerance,
            max_depth=(
                tolerance.max_integration_depth
            ),
        )

    def length_to(
        self,
        t: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        parameter = _unit_parameter(
            t
        )

        if parameter == 0.0:
            return 0.0

        if self.is_zero_length(
            tolerance=tolerance
        ):
            return 0.0

        if self.is_line_like(
            tolerance=tolerance
        ):
            return (
                self.start.distance_to(
                    self.end
                )
                * parameter
            )

        if parameter == 1.0:
            return self.length(
                tolerance=tolerance
            )

        return _adaptive_simpson(
            self._speed,
            0.0,
            parameter,
            tolerance.length_tolerance,
            max_depth=(
                tolerance.max_integration_depth
            ),
        )


# ---------------------------------------------------------------------------
# Arc to cubic derived approximation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArcBezierApproximation:
    segments: tuple[
        CubicBezierSegment,
        ...
    ]
    requested_tolerance: float
    observed_error: float
    recursion_depth: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requested_tolerance",
            _positive_finite(
                self.requested_tolerance,
                name="requested_tolerance",
                path="geometry/arc-approximation",
            ),
        )

        object.__setattr__(
            self,
            "observed_error",
            _positive_finite(
                self.observed_error,
                name="observed_error",
                path="geometry/arc-approximation",
                allow_zero=True,
            ),
        )

        if (
            isinstance(
                self.recursion_depth,
                bool,
            )
            or not isinstance(
                self.recursion_depth,
                int,
            )
            or self.recursion_depth < 0
        ):
            raise InvalidGeometryError(
                "arc approximation recursion_depth must be a non-negative integer",
                path="geometry/arc-approximation",
            )


def _arc_interval_cubic(
    parameters: ArcCenterParameters,
    start_angle: float,
    end_angle: float,
) -> CubicBezierSegment:
    delta = (
        end_angle
        - start_angle
    )

    start = _arc_point_at_angle(
        parameters,
        start_angle,
    )

    end = _arc_point_at_angle(
        parameters,
        end_angle,
    )

    start_derivative = (
        _arc_derivative_angle(
            parameters,
            start_angle,
        )
    )

    end_derivative = (
        _arc_derivative_angle(
            parameters,
            end_angle,
        )
    )

    alpha = (
        4.0
        / 3.0
        * math.tan(
            delta / 4.0
        )
    )

    return CubicBezierSegment(
        start=start,
        control1=(
            start
            + start_derivative
            * alpha
        ),
        control2=(
            end
            - end_derivative
            * alpha
        ),
        end=end,
    )


def arc_to_cubic_beziers(
    arc: EllipticalArcSegment,
    *,
    tolerance: float | None = None,
    policy: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> ArcBezierApproximation:
    requested = (
        policy.arc_approximation_tolerance
        if tolerance is None
        else _positive_finite(
            tolerance,
            name="arc approximation tolerance",
            path="geometry/arc-approximation",
        )
    )

    if arc.is_zero_length(
        tolerance=policy
    ):
        point = arc.start

        segment = CubicBezierSegment(
            point,
            point,
            point,
            point,
        )

        return ArcBezierApproximation(
            segments=(
                segment,
            ),
            requested_tolerance=requested,
            observed_error=0.0,
            recursion_depth=0,
        )

    if arc.is_line_like(
        tolerance=policy
    ):
        first = arc.start.lerp(
            arc.end,
            1.0 / 3.0,
        )

        second = arc.start.lerp(
            arc.end,
            2.0 / 3.0,
        )

        segment = CubicBezierSegment(
            arc.start,
            first,
            second,
            arc.end,
        )

        return ArcBezierApproximation(
            segments=(
                segment,
            ),
            requested_tolerance=requested,
            observed_error=0.0,
            recursion_depth=0,
        )

    parameters = arc.center_parameters(
        tolerance=policy
    )

    accepted: list[
        CubicBezierSegment
    ] = []

    maximum_error = 0.0
    maximum_depth = 0

    def recurse(
        angle_start: float,
        angle_end: float,
        depth: int,
    ) -> None:
        nonlocal maximum_error
        nonlocal maximum_depth

        cubic = _arc_interval_cubic(
            parameters,
            angle_start,
            angle_end,
        )

        interval = (
            angle_end
            - angle_start
        )

        error = 0.0

        for sample in (
            0.25,
            0.5,
            0.75,
        ):
            arc_point = _arc_point_at_angle(
                parameters,
                (
                    angle_start
                    + interval
                    * sample
                ),
            )

            cubic_point = cubic.point_at(
                sample
            )

            error = max(
                error,
                arc_point.distance_to(
                    cubic_point
                ),
            )

        maximum_error = max(
            maximum_error,
            error,
        )

        maximum_depth = max(
            maximum_depth,
            depth,
        )

        if (
            error <= requested
            or depth
            >= policy.max_arc_approximation_depth
        ):
            accepted.append(
                cubic
            )
            return

        midpoint = (
            angle_start
            + angle_end
        ) / 2.0

        recurse(
            angle_start,
            midpoint,
            depth + 1,
        )

        recurse(
            midpoint,
            angle_end,
            depth + 1,
        )

    recurse(
        parameters.start_angle,
        parameters.end_angle,
        0,
    )

    return ArcBezierApproximation(
        segments=tuple(
            accepted
        ),
        requested_tolerance=requested,
        observed_error=maximum_error,
        recursion_depth=maximum_depth,
    )


GeometricSegment: TypeAlias = (
    LineSegment
    | QuadraticBezierSegment
    | CubicBezierSegment
    | EllipticalArcSegment
)


# ---------------------------------------------------------------------------
# Fill rule
# ---------------------------------------------------------------------------


class FillRule(StrEnum):
    NONZERO = "nonzero"
    EVENODD = "evenodd"


# ---------------------------------------------------------------------------
# Canonical path commands
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MoveTo:
    end: Point


@dataclass(frozen=True, slots=True)
class LineTo:
    end: Point


@dataclass(frozen=True, slots=True)
class QuadraticTo:
    control: Point
    end: Point


@dataclass(frozen=True, slots=True)
class CubicTo:
    control1: Point
    control2: Point
    end: Point


@dataclass(frozen=True, slots=True)
class ArcTo:
    rx: float
    ry: float
    x_axis_rotation: float
    large_arc: bool
    sweep: bool
    end: Point

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rx",
            _positive_finite(
                self.rx,
                name="arc.rx",
                path="geometry/path-command",
                allow_zero=True,
            ),
        )

        object.__setattr__(
            self,
            "ry",
            _positive_finite(
                self.ry,
                name="arc.ry",
                path="geometry/path-command",
                allow_zero=True,
            ),
        )

        object.__setattr__(
            self,
            "x_axis_rotation",
            normalize_degrees(
                _finite_real(
                    self.x_axis_rotation,
                    name="arc.x_axis_rotation",
                    path="geometry/path-command",
                )
            ),
        )

        if not isinstance(
            self.large_arc,
            bool,
        ):
            raise PathGeometryError(
                "ArcTo large_arc must be boolean",
                path="geometry/path-command",
            )

        if not isinstance(
            self.sweep,
            bool,
        ):
            raise PathGeometryError(
                "ArcTo sweep must be boolean",
                path="geometry/path-command",
            )


@dataclass(frozen=True, slots=True)
class ClosePath:
    pass


PathCommand: TypeAlias = (
    MoveTo
    | LineTo
    | QuadraticTo
    | CubicTo
    | ArcTo
    | ClosePath
)


# ---------------------------------------------------------------------------
# Path segment records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SegmentRecord:
    segment: GeometricSegment
    command_index: int
    subpath_index: int
    closing: bool = False


@dataclass(frozen=True, slots=True)
class ApproximationRecord:
    operation: str
    command_index: int
    requested_tolerance: float
    observed_error: float
    generated_segment_count: int


@dataclass(frozen=True, slots=True)
class PathTransformResult:
    path: Path
    approximations: tuple[
        ApproximationRecord,
        ...
    ] = ()


# ---------------------------------------------------------------------------
# Canonical path
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Path:
    commands: tuple[
        PathCommand,
        ...
    ] = ()

    fill_rule: FillRule = (
        FillRule.NONZERO
    )

    schema: str = PATH_SCHEMA

    def __post_init__(self) -> None:
        commands = tuple(
            self.commands
        )

        if not isinstance(
            self.fill_rule,
            FillRule,
        ):
            try:
                fill_rule = FillRule(
                    self.fill_rule
                )
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise PathGeometryError(
                    "invalid path fill rule",
                    path="geometry/path",
                ) from exc

            object.__setattr__(
                self,
                "fill_rule",
                fill_rule,
            )

        for command in commands:
            if not isinstance(
                command,
                (
                    MoveTo,
                    LineTo,
                    QuadraticTo,
                    CubicTo,
                    ArcTo,
                    ClosePath,
                ),
            ):
                raise PathGeometryError(
                    "unsupported canonical path command",
                    path="geometry/path",
                    context={
                        "command_type": (
                            type(
                                command
                            ).__name__
                        ),
                    },
                )

        object.__setattr__(
            self,
            "commands",
            commands,
        )

        self._validate_topology()

    def _validate_topology(
        self,
    ) -> None:
        active = False

        for index, command in enumerate(
            self.commands
        ):
            if isinstance(
                command,
                MoveTo,
            ):
                active = True
                continue

            if not active:
                raise PathTopologyError(
                    "drawing command encountered before initial MoveTo",
                    path=(
                        f"geometry/path/command[{index}]"
                    ),
                    context={
                        "command_type": (
                            type(
                                command
                            ).__name__
                        ),
                    },
                )

    @property
    def command_count(self) -> int:
        return len(
            self.commands
        )

    @property
    def subpath_count(self) -> int:
        return sum(
            1
            for command in self.commands
            if isinstance(
                command,
                MoveTo,
            )
        )

    def iter_segments(
        self,
    ) -> Iterator[
        SegmentRecord
    ]:
        current: Point | None = None
        subpath_start: Point | None = None
        subpath_index = -1

        for command_index, command in enumerate(
            self.commands
        ):
            if isinstance(
                command,
                MoveTo,
            ):
                current = command.end
                subpath_start = command.end
                subpath_index += 1
                continue

            if current is None:
                raise PathTopologyError(
                    "path segment has no current point",
                    path=(
                        f"geometry/path/command[{command_index}]"
                    ),
                )

            if isinstance(
                command,
                LineTo,
            ):
                segment = LineSegment(
                    current,
                    command.end,
                )

                yield SegmentRecord(
                    segment=segment,
                    command_index=command_index,
                    subpath_index=subpath_index,
                )

                current = command.end
                continue

            if isinstance(
                command,
                QuadraticTo,
            ):
                segment = (
                    QuadraticBezierSegment(
                        current,
                        command.control,
                        command.end,
                    )
                )

                yield SegmentRecord(
                    segment=segment,
                    command_index=command_index,
                    subpath_index=subpath_index,
                )

                current = command.end
                continue

            if isinstance(
                command,
                CubicTo,
            ):
                segment = (
                    CubicBezierSegment(
                        current,
                        command.control1,
                        command.control2,
                        command.end,
                    )
                )

                yield SegmentRecord(
                    segment=segment,
                    command_index=command_index,
                    subpath_index=subpath_index,
                )

                current = command.end
                continue

            if isinstance(
                command,
                ArcTo,
            ):
                segment = (
                    EllipticalArcSegment(
                        start=current,
                        rx=command.rx,
                        ry=command.ry,
                        x_axis_rotation=(
                            command.x_axis_rotation
                        ),
                        large_arc=(
                            command.large_arc
                        ),
                        sweep=command.sweep,
                        end=command.end,
                    )
                )

                yield SegmentRecord(
                    segment=segment,
                    command_index=command_index,
                    subpath_index=subpath_index,
                )

                current = command.end
                continue

            if isinstance(
                command,
                ClosePath,
            ):
                if subpath_start is None:
                    raise PathTopologyError(
                        "ClosePath has no active subpath start",
                        path=(
                            f"geometry/path/command[{command_index}]"
                        ),
                    )

                segment = LineSegment(
                    current,
                    subpath_start,
                )

                yield SegmentRecord(
                    segment=segment,
                    command_index=command_index,
                    subpath_index=subpath_index,
                    closing=True,
                )

                current = (
                    subpath_start
                )
                continue

            raise PathGeometryError(
                "unreachable canonical path command",
                path=(
                    f"geometry/path/command[{command_index}]"
                ),
            )

    @property
    def segment_count(self) -> int:
        return sum(
            1
            for _ in self.iter_segments()
        )

    def bounds(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Bounds | None:
        result: Bounds | None = None

        for record in self.iter_segments():
            segment_bounds = (
                record.segment.bounds(
                    tolerance=tolerance
                )
            )

            result = (
                segment_bounds
                if result is None
                else result.union(
                    segment_bounds
                )
            )

        return result

    def length(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> float:
        return math.fsum(
            record.segment.length(
                tolerance=tolerance
            )
            for record
            in self.iter_segments()
        )

    def subpath_lengths(
        self,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> tuple[float, ...]:
        counts = [
            0.0
            for _ in range(
                self.subpath_count
            )
        ]

        for record in self.iter_segments():
            counts[
                record.subpath_index
            ] += record.segment.length(
                tolerance=tolerance
            )

        return tuple(
            counts
        )

    def _parameter_for_segment_length(
        self,
        segment: GeometricSegment,
        distance: float,
        *,
        tolerance: TolerancePolicy,
    ) -> float:
        segment_length = (
            segment.length(
                tolerance=tolerance
            )
        )

        if segment_length <= tolerance.epsilon:
            return 0.0

        if distance <= 0.0:
            return 0.0

        if distance >= segment_length:
            return 1.0

        if isinstance(
            segment,
            LineSegment,
        ):
            return (
                distance
                / segment_length
            )

        lower = 0.0
        upper = 1.0

        for _ in range(56):
            midpoint = (
                lower
                + upper
            ) / 2.0

            current = (
                segment.length_to(
                    midpoint,
                    tolerance=tolerance,
                )
            )

            if (
                abs(
                    current - distance
                )
                <= tolerance.length_tolerance
            ):
                return midpoint

            if current < distance:
                lower = midpoint
            else:
                upper = midpoint

        return (
            lower
            + upper
        ) / 2.0

    def point_at_length(
        self,
        distance: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Point:
        target = _finite_real(
            distance,
            name="distance",
            path="geometry/path",
        )

        records = tuple(
            self.iter_segments()
        )

        if not records:
            raise DegenerateGeometryError(
                "cannot evaluate point-at-length on a path with no drawable segments",
                path="geometry/path",
            )

        total = math.fsum(
            record.segment.length(
                tolerance=tolerance
            )
            for record in records
        )

        target = clamp(
            target,
            0.0,
            total,
        )

        consumed = 0.0

        for record in records:
            segment_length = (
                record.segment.length(
                    tolerance=tolerance
                )
            )

            if (
                target
                <= consumed
                + segment_length
                + tolerance.length_tolerance
            ):
                local_distance = max(
                    0.0,
                    target - consumed,
                )

                parameter = (
                    self._parameter_for_segment_length(
                        record.segment,
                        local_distance,
                        tolerance=tolerance,
                    )
                )

                return record.segment.point_at(
                    parameter
                )

            consumed += segment_length

        return records[
            -1
        ].segment.end

    def tangent_at_length(
        self,
        distance: Real,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Vector:
        target = _finite_real(
            distance,
            name="distance",
            path="geometry/path",
        )

        records = tuple(
            self.iter_segments()
        )

        if not records:
            raise DegenerateGeometryError(
                "cannot evaluate tangent-at-length on a path with no drawable segments",
                path="geometry/path",
            )

        total = math.fsum(
            record.segment.length(
                tolerance=tolerance
            )
            for record in records
        )

        target = clamp(
            target,
            0.0,
            total,
        )

        consumed = 0.0

        for record in records:
            segment_length = (
                record.segment.length(
                    tolerance=tolerance
                )
            )

            if (
                target
                <= consumed
                + segment_length
                + tolerance.length_tolerance
            ):
                local_distance = max(
                    0.0,
                    target - consumed,
                )

                parameter = (
                    self._parameter_for_segment_length(
                        record.segment,
                        local_distance,
                        tolerance=tolerance,
                    )
                )

                return record.segment.tangent_at(
                    parameter,
                    tolerance=tolerance,
                )

            consumed += segment_length

        return records[
            -1
        ].segment.tangent_at(
            1.0,
            tolerance=tolerance,
        )

    def normalized(
        self,
        *,
        preserve_empty_subpaths: bool = True,
    ) -> Path:
        """
        Deterministic command normalization.

        Numeric values are already normalized by command construction.
        This pass only removes semantically inert duplicate structure when
        policy allows it.
        """

        output: list[
            PathCommand
        ] = []

        current_subpath_has_drawing = False
        previous_was_close = False

        for command in self.commands:
            if isinstance(
                command,
                MoveTo,
            ):
                if (
                    output
                    and isinstance(
                        output[-1],
                        MoveTo,
                    )
                    and not preserve_empty_subpaths
                ):
                    output[-1] = command
                else:
                    output.append(
                        command
                    )

                current_subpath_has_drawing = False
                previous_was_close = False
                continue

            if isinstance(
                command,
                ClosePath,
            ):
                if previous_was_close:
                    continue

                output.append(
                    command
                )

                previous_was_close = True
                continue

            output.append(
                command
            )

            current_subpath_has_drawing = True
            previous_was_close = False

        return Path(
            commands=tuple(
                output
            ),
            fill_rule=self.fill_rule,
        )

    def transformed(
        self,
        transform: AffineTransform,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> PathTransformResult:
        """
        Derive a transformed canonical path.

        Lines and Béziers remain exact under affine transformation.

        Elliptical arcs remain endpoint-form arcs only for positive
        uniform scale+rotation transforms. Under general affine
        transforms, the arc is deterministically approximated with cubic
        Bézier segments and approximation provenance is returned.
        """

        output: list[
            PathCommand
        ] = []

        approximations: list[
            ApproximationRecord
        ] = []

        current: Point | None = None
        subpath_start: Point | None = None

        similarity = (
            transform.positive_uniform_similarity(
                tolerance=tolerance
            )
        )

        for index, command in enumerate(
            self.commands
        ):
            if isinstance(
                command,
                MoveTo,
            ):
                output.append(
                    MoveTo(
                        transform.apply_point(
                            command.end
                        )
                    )
                )

                current = command.end
                subpath_start = command.end
                continue

            if current is None:
                raise PathTopologyError(
                    "transformation encountered a drawing command without current point",
                    path=(
                        f"geometry/path/command[{index}]"
                    ),
                )

            if isinstance(
                command,
                LineTo,
            ):
                output.append(
                    LineTo(
                        transform.apply_point(
                            command.end
                        )
                    )
                )

                current = command.end
                continue

            if isinstance(
                command,
                QuadraticTo,
            ):
                output.append(
                    QuadraticTo(
                        control=(
                            transform.apply_point(
                                command.control
                            )
                        ),
                        end=(
                            transform.apply_point(
                                command.end
                            )
                        ),
                    )
                )

                current = command.end
                continue

            if isinstance(
                command,
                CubicTo,
            ):
                output.append(
                    CubicTo(
                        control1=(
                            transform.apply_point(
                                command.control1
                            )
                        ),
                        control2=(
                            transform.apply_point(
                                command.control2
                            )
                        ),
                        end=(
                            transform.apply_point(
                                command.end
                            )
                        ),
                    )
                )

                current = command.end
                continue

            if isinstance(
                command,
                ArcTo,
            ):
                arc = (
                    EllipticalArcSegment(
                        start=current,
                        rx=command.rx,
                        ry=command.ry,
                        x_axis_rotation=(
                            command.x_axis_rotation
                        ),
                        large_arc=(
                            command.large_arc
                        ),
                        sweep=command.sweep,
                        end=command.end,
                    )
                )

                if arc.is_zero_length(
                    tolerance=tolerance
                ):
                    current = command.end
                    continue

                if arc.is_line_like(
                    tolerance=tolerance
                ):
                    output.append(
                        LineTo(
                            transform.apply_point(
                                command.end
                            )
                        )
                    )

                    current = command.end
                    continue

                if similarity is not None:
                    scale, rotation = (
                        similarity
                    )

                    output.append(
                        ArcTo(
                            rx=(
                                command.rx
                                * scale
                            ),
                            ry=(
                                command.ry
                                * scale
                            ),
                            x_axis_rotation=(
                                command.x_axis_rotation
                                + rotation
                            ),
                            large_arc=(
                                command.large_arc
                            ),
                            sweep=command.sweep,
                            end=(
                                transform.apply_point(
                                    command.end
                                )
                            ),
                        )
                    )

                    current = command.end
                    continue

                approximation = (
                    arc_to_cubic_beziers(
                        arc,
                        tolerance=(
                            tolerance.arc_approximation_tolerance
                        ),
                        policy=tolerance,
                    )
                )

                for segment in approximation.segments:
                    output.append(
                        CubicTo(
                            control1=(
                                transform.apply_point(
                                    segment.control1
                                )
                            ),
                            control2=(
                                transform.apply_point(
                                    segment.control2
                                )
                            ),
                            end=(
                                transform.apply_point(
                                    segment.end
                                )
                            ),
                        )
                    )

                approximations.append(
                    ApproximationRecord(
                        operation=(
                            "affine-transform-arc-to-cubic"
                        ),
                        command_index=index,
                        requested_tolerance=(
                            approximation.requested_tolerance
                        ),
                        observed_error=(
                            approximation.observed_error
                        ),
                        generated_segment_count=(
                            len(
                                approximation.segments
                            )
                        ),
                    )
                )

                current = command.end
                continue

            if isinstance(
                command,
                ClosePath,
            ):
                output.append(
                    ClosePath()
                )

                if subpath_start is not None:
                    current = (
                        subpath_start
                    )

                continue

            raise PathGeometryError(
                "unreachable canonical path command during transformation",
                path=(
                    f"geometry/path/command[{index}]"
                ),
            )

        return PathTransformResult(
            path=Path(
                commands=tuple(
                    output
                ),
                fill_rule=self.fill_rule,
            ),
            approximations=tuple(
                approximations
            ),
        )


# ---------------------------------------------------------------------------
# Curve flattening
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FlattenedSubpath:
    points: tuple[
        Point,
        ...
    ]
    closed: bool


@dataclass(frozen=True, slots=True)
class FlattenedPath:
    subpaths: tuple[
        FlattenedSubpath,
        ...
    ]
    tolerance: float


def _distance_point_to_line(
    point: Point,
    start: Point,
    end: Point,
    *,
    tolerance: TolerancePolicy,
) -> float:
    line = (
        end
        - start
    )

    magnitude = (
        line.magnitude
    )

    if magnitude <= tolerance.epsilon:
        return point.distance_to(
            start
        )

    offset = (
        point
        - start
    )

    return abs(
        offset.cross(
            line
        )
    ) / magnitude


def _flatten_quadratic(
    segment: QuadraticBezierSegment,
    *,
    tolerance_value: float,
    policy: TolerancePolicy,
    depth: int,
) -> tuple[Point, ...]:
    flatness = (
        _distance_point_to_line(
            segment.control,
            segment.start,
            segment.end,
            tolerance=policy,
        )
    )

    if (
        flatness
        <= tolerance_value
        or depth
        >= policy.max_flattening_depth
    ):
        return (
            segment.start,
            segment.end,
        )

    left, right = segment.subdivide(
        0.5
    )

    left_points = _flatten_quadratic(
        left,
        tolerance_value=tolerance_value,
        policy=policy,
        depth=depth + 1,
    )

    right_points = _flatten_quadratic(
        right,
        tolerance_value=tolerance_value,
        policy=policy,
        depth=depth + 1,
    )

    return (
        left_points[:-1]
        + right_points
    )


def _flatten_cubic(
    segment: CubicBezierSegment,
    *,
    tolerance_value: float,
    policy: TolerancePolicy,
    depth: int,
) -> tuple[Point, ...]:
    flatness = max(
        _distance_point_to_line(
            segment.control1,
            segment.start,
            segment.end,
            tolerance=policy,
        ),
        _distance_point_to_line(
            segment.control2,
            segment.start,
            segment.end,
            tolerance=policy,
        ),
    )

    if (
        flatness
        <= tolerance_value
        or depth
        >= policy.max_flattening_depth
    ):
        return (
            segment.start,
            segment.end,
        )

    left, right = segment.subdivide(
        0.5
    )

    left_points = _flatten_cubic(
        left,
        tolerance_value=tolerance_value,
        policy=policy,
        depth=depth + 1,
    )

    right_points = _flatten_cubic(
        right,
        tolerance_value=tolerance_value,
        policy=policy,
        depth=depth + 1,
    )

    return (
        left_points[:-1]
        + right_points
    )


def flatten_segment(
    segment: GeometricSegment,
    *,
    tolerance: float | None = None,
    policy: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> tuple[Point, ...]:
    requested = (
        policy.flattening_tolerance
        if tolerance is None
        else _positive_finite(
            tolerance,
            name="flattening tolerance",
            path="geometry/flatten",
        )
    )

    if isinstance(
        segment,
        LineSegment,
    ):
        return (
            segment.start,
            segment.end,
        )

    if isinstance(
        segment,
        QuadraticBezierSegment,
    ):
        return _flatten_quadratic(
            segment,
            tolerance_value=requested,
            policy=policy,
            depth=0,
        )

    if isinstance(
        segment,
        CubicBezierSegment,
    ):
        return _flatten_cubic(
            segment,
            tolerance_value=requested,
            policy=policy,
            depth=0,
        )

    if isinstance(
        segment,
        EllipticalArcSegment,
    ):
        approximation = (
            arc_to_cubic_beziers(
                segment,
                tolerance=min(
                    requested,
                    policy.arc_approximation_tolerance,
                ),
                policy=policy,
            )
        )

        output: list[
            Point
        ] = []

        for cubic in approximation.segments:
            points = _flatten_cubic(
                cubic,
                tolerance_value=requested,
                policy=policy,
                depth=0,
            )

            if output:
                output.extend(
                    points[1:]
                )
            else:
                output.extend(
                    points
                )

        return tuple(
            output
        )

    raise InvalidGeometryError(
        "unsupported segment type for flattening",
        path="geometry/flatten",
        context={
            "segment_type": (
                type(
                    segment
                ).__name__
            ),
        },
    )


def flatten_path(
    path: Path,
    *,
    tolerance: float | None = None,
    policy: TolerancePolicy = (
        DEFAULT_TOLERANCE
    ),
) -> FlattenedPath:
    requested = (
        policy.flattening_tolerance
        if tolerance is None
        else _positive_finite(
            tolerance,
            name="flattening tolerance",
            path="geometry/flatten",
        )
    )

    subpath_points: list[
        list[Point]
    ] = []

    subpath_closed: list[
        bool
    ] = []

    for _ in range(
        path.subpath_count
    ):
        subpath_points.append(
            []
        )
        subpath_closed.append(
            False
        )

    move_points: list[
        Point
    ] = [
        command.end
        for command in path.commands
        if isinstance(
            command,
            MoveTo,
        )
    ]

    for index, point in enumerate(
        move_points
    ):
        subpath_points[
            index
        ].append(
            point
        )

    for record in path.iter_segments():
        points = flatten_segment(
            record.segment,
            tolerance=requested,
            policy=policy,
        )

        target = subpath_points[
            record.subpath_index
        ]

        if not target:
            target.extend(
                points
            )
        elif points:
            if (
                target[-1]
                == points[0]
            ):
                target.extend(
                    points[1:]
                )
            else:
                target.extend(
                    points
                )

        if record.closing:
            subpath_closed[
                record.subpath_index
            ] = True

    result = tuple(
        FlattenedSubpath(
            points=tuple(
                points
            ),
            closed=(
                subpath_closed[
                    index
                ]
            ),
        )
        for index, points
        in enumerate(
            subpath_points
        )
    )

    return FlattenedPath(
        subpaths=result,
        tolerance=requested,
    )


# ---------------------------------------------------------------------------
# Stroke-aware conservative bounds
# ---------------------------------------------------------------------------


class StrokeLineJoin(StrEnum):
    MITER = "miter"
    ROUND = "round"
    BEVEL = "bevel"


class StrokeLineCap(StrEnum):
    BUTT = "butt"
    ROUND = "round"
    SQUARE = "square"


def stroke_aware_bounds(
    geometry_bounds: Bounds,
    *,
    width: Real,
    line_join: StrokeLineJoin = (
        StrokeLineJoin.MITER
    ),
    miter_limit: Real = 4.0,
) -> Bounds:
    stroke_width = (
        _positive_finite(
            width,
            name="stroke width",
            path="geometry/stroke",
            allow_zero=True,
        )
    )

    if not isinstance(
        line_join,
        StrokeLineJoin,
    ):
        line_join = StrokeLineJoin(
            line_join
        )

    limit = _positive_finite(
        miter_limit,
        name="miter_limit",
        path="geometry/stroke",
    )

    half = (
        stroke_width
        / 2.0
    )

    if (
        line_join
        == StrokeLineJoin.MITER
    ):
        expansion = max(
            half,
            half * limit,
        )
    else:
        expansion = half

    return geometry_bounds.expanded(
        expansion
    )


# ---------------------------------------------------------------------------
# Backend-neutral advanced geometry boundary
# ---------------------------------------------------------------------------


class BooleanOperation(StrEnum):
    UNION = "union"
    INTERSECTION = "intersection"
    DIFFERENCE = "difference"
    XOR = "xor"


@runtime_checkable
class GeometryBackend(Protocol):
    """
    Optional advanced computational geometry backend.

    Backend-specific representations must never escape this interface.
    """

    @property
    def backend_id(self) -> str:
        ...

    @property
    def backend_version(self) -> str:
        ...

    def boolean(
        self,
        operation: BooleanOperation,
        left: Path,
        right: Path,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Path:
        ...

    def offset(
        self,
        path: Path,
        distance: float,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Path:
        ...

    def stroke_to_path(
        self,
        path: Path,
        *,
        width: float,
        line_join: StrokeLineJoin,
        line_cap: StrokeLineCap,
        miter_limit: float,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Path:
        ...


@dataclass(frozen=True, slots=True)
class NativeGeometryBackend:
    """
    Native deterministic geometry capability declaration.

    The native kernel intentionally refuses unreliable general boolean and
    offset operations rather than pretending to implement them.
    """

    backend_id: str = "savant-native-geometry"
    backend_version: str = MODULE_VERSION

    def boolean(
        self,
        operation: BooleanOperation,
        left: Path,
        right: Path,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Path:
        del left
        del right
        del tolerance

        raise UnsupportedFeatureError(
            (
                "general path boolean operation "
                f"{operation.value!r} requires an approved "
                "advanced geometry backend"
            ),
            path="geometry/backend",
            context={
                "backend": self.backend_id,
                "operation": operation.value,
            },
        )

    def offset(
        self,
        path: Path,
        distance: float,
        *,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Path:
        del path
        del tolerance

        _finite_real(
            distance,
            name="offset distance",
            path="geometry/backend",
        )

        raise UnsupportedFeatureError(
            "path offsetting requires an approved advanced geometry backend",
            path="geometry/backend",
            context={
                "backend": self.backend_id,
            },
        )

    def stroke_to_path(
        self,
        path: Path,
        *,
        width: float,
        line_join: StrokeLineJoin,
        line_cap: StrokeLineCap,
        miter_limit: float,
        tolerance: TolerancePolicy = (
            DEFAULT_TOLERANCE
        ),
    ) -> Path:
        del path
        del line_join
        del line_cap
        del tolerance

        _positive_finite(
            width,
            name="stroke width",
            path="geometry/backend",
            allow_zero=True,
        )

        _positive_finite(
            miter_limit,
            name="miter limit",
            path="geometry/backend",
        )

        raise UnsupportedFeatureError(
            "stroke-to-path conversion requires an approved advanced geometry backend",
            path="geometry/backend",
            context={
                "backend": self.backend_id,
            },
        )


NATIVE_GEOMETRY_BACKEND: Final[
    NativeGeometryBackend
] = NativeGeometryBackend()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


__all__ = [
    "GEOMETRY_SCHEMA",
    "PATH_SCHEMA",
    "MODULE_VERSION",
    "TAU",
    "PI",
    "HALF_PI",

    "TolerancePolicy",
    "DEFAULT_TOLERANCE",

    "normalize_zero",
    "normalize_angle_radians",
    "normalize_degrees",
    "clamp",
    "lerp_scalar",

    "Point",
    "Vector",
    "ORIGIN",
    "ZERO_VECTOR",

    "Bounds",
    "union_bounds",

    "AffineTransform",
    "IDENTITY_TRANSFORM",

    "Segment",
    "LineSegment",
    "QuadraticBezierSegment",
    "CubicBezierSegment",
    "EllipticalArcSegment",
    "GeometricSegment",

    "ArcCenterParameters",
    "ArcBezierApproximation",
    "arc_to_cubic_beziers",

    "FillRule",

    "MoveTo",
    "LineTo",
    "QuadraticTo",
    "CubicTo",
    "ArcTo",
    "ClosePath",
    "PathCommand",

    "SegmentRecord",
    "ApproximationRecord",
    "PathTransformResult",
    "Path",

    "FlattenedSubpath",
    "FlattenedPath",
    "flatten_segment",
    "flatten_path",

    "StrokeLineJoin",
    "StrokeLineCap",
    "stroke_aware_bounds",

    "BooleanOperation",
    "GeometryBackend",
    "NativeGeometryBackend",
    "NATIVE_GEOMETRY_BACKEND",
]
