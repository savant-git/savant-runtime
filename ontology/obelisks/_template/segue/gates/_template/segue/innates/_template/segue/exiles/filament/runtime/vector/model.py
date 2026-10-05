"""
SAVANT Filament Vector Renderer
Canonical immutable semantic scene model.

This module defines the authoritative in-memory vector scene substance used
by the Filament renderer before validation, normalization, dependency
resolution, or SVG projection.

The scene model deliberately separates semantic vector meaning from SVG
syntax. It models geometry, appearance, composition, definitions, resources,
text, accessibility, and reusable instances as immutable Python value objects.

Architectural rules:

* scene substance is immutable by compilation time;
* geometry is represented by geometry.py objects, never raw SVG path strings;
* paint is a typed algebra, never raw CSS/SVG paint text;
* definitions are semantic objects with stable semantic identities;
* nodes reference definitions through typed references instead of textual
  ``url(#...)`` strings;
* groups preserve compositing semantics such as group opacity and isolation;
* components are substantiated once and referenced by instances;
* masks, clips, gradients, patterns, markers, and filter graphs are first-class
  reusable definitions;
* resources are classified as embedded, local, or external and are never
  fetched merely by constructing a scene;
* text remains Unicode semantic content. Shaping and outline conversion are
  backend responsibilities outside this module;
* metadata, accessibility, and interaction information are deterministic value
  objects rather than arbitrary mutable dictionaries;
* compilation-time caches, generated SVG IDs, backend handles, diagnostics,
  and serializer state never live in canonical scene objects.

This module has no third-party dependencies.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
import math
from numbers import Real
from typing import ClassVar, Final, Protocol, Self, TypeAlias, runtime_checkable

try:
    from .errors import (
        ResourcePolicyError,
        SceneSchemaError,
    )
    from .geometry import (
        AffineTransform,
        FillRule,
        IDENTITY_TRANSFORM,
        Path as GeometryPath,
        Point,
        StrokeLineCap,
        StrokeLineJoin,
    )
except ImportError:
    from errors import (
        ResourcePolicyError,
        SceneSchemaError,
    )
    from geometry import (
        AffineTransform,
        FillRule,
        IDENTITY_TRANSFORM,
        Path as GeometryPath,
        Point,
        StrokeLineCap,
        StrokeLineJoin,
    )


MODEL_SCHEMA: Final[str] = (
    "savant://filament/vector/model/1.0.0"
)

SCENE_SCHEMA: Final[str] = (
    "savant://filament/vector/scene/1.0.0"
)

RESOURCE_SCHEMA: Final[str] = (
    "savant://filament/vector/resource/1.0.0"
)

MODULE_VERSION: Final[str] = "1.0.0"


# ---------------------------------------------------------------------------
# Shared scalar validation
# ---------------------------------------------------------------------------


def _finite_number(
    value: Real,
    *,
    name: str,
    path: str = "scene",
) -> float:
    """
    Normalize one canonical finite real number.

    Numeric strings are deliberately rejected. Parsers and importers must
    normalize textual input before it reaches canonical scene substance.
    """

    if isinstance(value, bool) or not isinstance(value, Real):
        raise SceneSchemaError(
            f"{name} must be a finite real number",
            path=path,
            context={
                "field": name,
                "received_type": type(value).__name__,
            },
        )

    result = float(value)

    if not math.isfinite(result):
        raise SceneSchemaError(
            f"{name} must be finite",
            path=path,
            context={
                "field": name,
            },
        )

    if result == 0.0:
        return 0.0

    return result


def _non_negative_number(
    value: Real,
    *,
    name: str,
    path: str = "scene",
) -> float:
    result = _finite_number(
        value,
        name=name,
        path=path,
    )

    if result < 0.0:
        raise SceneSchemaError(
            f"{name} must be non-negative",
            path=path,
            context={
                "field": name,
                "value": result,
            },
        )

    return result


def _positive_number(
    value: Real,
    *,
    name: str,
    path: str = "scene",
) -> float:
    result = _finite_number(
        value,
        name=name,
        path=path,
    )

    if result <= 0.0:
        raise SceneSchemaError(
            f"{name} must be positive",
            path=path,
            context={
                "field": name,
                "value": result,
            },
        )

    return result


def _unit_interval(
    value: Real,
    *,
    name: str,
    path: str = "scene",
) -> float:
    result = _finite_number(
        value,
        name=name,
        path=path,
    )

    if not 0.0 <= result <= 1.0:
        raise SceneSchemaError(
            f"{name} must lie within [0, 1]",
            path=path,
            context={
                "field": name,
                "value": result,
            },
        )

    return result


def _optional_nonempty_text(
    value: str | None,
    *,
    name: str,
    path: str = "scene",
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise SceneSchemaError(
            f"{name} must be a string or None",
            path=path,
            context={
                "field": name,
                "received_type": type(value).__name__,
            },
        )

    normalized = value.strip()

    if not normalized:
        return None

    if "\x00" in normalized:
        raise SceneSchemaError(
            f"{name} must not contain NUL characters",
            path=path,
            context={
                "field": name,
            },
        )

    return normalized


def _required_nonempty_text(
    value: str,
    *,
    name: str,
    path: str = "scene",
) -> str:
    normalized = _optional_nonempty_text(
        value,
        name=name,
        path=path,
    )

    if normalized is None:
        raise SceneSchemaError(
            f"{name} must not be empty",
            path=path,
            context={
                "field": name,
            },
        )

    return normalized


def _normalized_classes(
    values: Iterable[str],
    *,
    path: str = "scene",
) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        item = _required_nonempty_text(
            value,
            name="class",
            path=path,
        )

        if any(
            character.isspace()
            for character in item
        ):
            raise SceneSchemaError(
                "class names must not contain whitespace",
                path=path,
                context={
                    "class": item,
                },
            )

        if item not in seen:
            seen.add(item)
            output.append(item)

    return tuple(output)


# ---------------------------------------------------------------------------
# Deterministic metadata
# ---------------------------------------------------------------------------


MetadataScalar: TypeAlias = (
    str
    | int
    | float
    | bool
    | None
)


def _normalize_metadata_scalar(
    value: MetadataScalar,
    *,
    key: str,
    path: str,
) -> MetadataScalar:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        if "\x00" in value:
            raise SceneSchemaError(
                "metadata strings must not contain NUL characters",
                path=path,
                context={
                    "key": key,
                },
            )

        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise SceneSchemaError(
                "metadata floating-point values must be finite",
                path=path,
                context={
                    "key": key,
                },
            )

        if value == 0.0:
            return 0.0

        return value

    raise SceneSchemaError(
        "metadata values must be deterministic scalar values",
        path=path,
        context={
            "key": key,
            "received_type": type(value).__name__,
        },
    )


@dataclass(
    frozen=True,
    slots=True,
    order=True,
)
class MetadataEntry:
    key: str
    value: MetadataScalar

    def __post_init__(self) -> None:
        key = _required_nonempty_text(
            self.key,
            name="metadata key",
            path="scene/metadata",
        )

        object.__setattr__(
            self,
            "key",
            key,
        )

        object.__setattr__(
            self,
            "value",
            _normalize_metadata_scalar(
                self.value,
                key=key,
                path="scene/metadata",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class Metadata:
    """
    Immutable deterministic semantic metadata.

    Canonical metadata supports scalar values. More complicated application
    structures should be represented by typed semantic objects rather than
    arbitrary mutable dictionaries.
    """

    entries: tuple[
        MetadataEntry,
        ...
    ] = ()

    def __post_init__(self) -> None:
        normalized: dict[
            str,
            MetadataEntry,
        ] = {}

        for entry in self.entries:
            if not isinstance(
                entry,
                MetadataEntry,
            ):
                raise SceneSchemaError(
                    "metadata entries must be MetadataEntry values",
                    path="scene/metadata",
                )

            if entry.key in normalized:
                raise SceneSchemaError(
                    "metadata keys must be unique",
                    path="scene/metadata",
                    context={
                        "key": entry.key,
                    },
                )

            normalized[
                entry.key
            ] = entry

        object.__setattr__(
            self,
            "entries",
            tuple(
                normalized[key]
                for key
                in sorted(normalized)
            ),
        )

    @classmethod
    def from_mapping(
        cls,
        values: (
            Mapping[
                str,
                MetadataScalar,
            ]
            | None
        ),
    ) -> Self:
        if not values:
            return cls()

        return cls(
            tuple(
                MetadataEntry(
                    key,
                    value,
                )
                for key, value
                in values.items()
            )
        )

    def get(
        self,
        key: str,
        default: MetadataScalar = None,
    ) -> MetadataScalar:
        for entry in self.entries:
            if entry.key == key:
                return entry.value

        return default

    def as_dict(
        self,
    ) -> dict[
        str,
        MetadataScalar,
    ]:
        return {
            entry.key: entry.value
            for entry in self.entries
        }

    def __bool__(
        self,
    ) -> bool:
        return bool(
            self.entries
        )

    def __iter__(
        self,
    ) -> Iterator[
        MetadataEntry
    ]:
        return iter(
            self.entries
        )


EMPTY_METADATA: Final[
    Metadata
] = Metadata()


# ---------------------------------------------------------------------------
# Scene policy primitives
# ---------------------------------------------------------------------------


class CoordinateSpacePolicy(
    StrEnum
):
    SVG_Y_DOWN = (
        "svg-y-down"
    )

    CARTESIAN_Y_UP = (
        "cartesian-y-up"
    )


class PreserveAspectAlign(
    StrEnum
):
    NONE = "none"

    X_MIN_Y_MIN = "xMinYMin"
    X_MID_Y_MIN = "xMidYMin"
    X_MAX_Y_MIN = "xMaxYMin"

    X_MIN_Y_MID = "xMinYMid"
    X_MID_Y_MID = "xMidYMid"
    X_MAX_Y_MID = "xMaxYMid"

    X_MIN_Y_MAX = "xMinYMax"
    X_MID_Y_MAX = "xMidYMax"
    X_MAX_Y_MAX = "xMaxYMax"


class MeetOrSlice(
    StrEnum
):
    MEET = "meet"
    SLICE = "slice"


@dataclass(
    frozen=True,
    slots=True,
)
class PreserveAspectRatio:
    align: PreserveAspectAlign = (
        PreserveAspectAlign.X_MID_Y_MID
    )

    meet_or_slice: MeetOrSlice = (
        MeetOrSlice.MEET
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.align,
            PreserveAspectAlign,
        ):
            object.__setattr__(
                self,
                "align",
                PreserveAspectAlign(
                    self.align
                ),
            )

        if not isinstance(
            self.meet_or_slice,
            MeetOrSlice,
        ):
            object.__setattr__(
                self,
                "meet_or_slice",
                MeetOrSlice(
                    self.meet_or_slice
                ),
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ViewBox:
    min_x: float
    min_y: float
    width: float
    height: float

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "min_x",
            _finite_number(
                self.min_x,
                name="viewbox.min_x",
                path="scene/viewbox",
            ),
        )

        object.__setattr__(
            self,
            "min_y",
            _finite_number(
                self.min_y,
                name="viewbox.min_y",
                path="scene/viewbox",
            ),
        )

        object.__setattr__(
            self,
            "width",
            _positive_number(
                self.width,
                name="viewbox.width",
                path="scene/viewbox",
            ),
        )

        object.__setattr__(
            self,
            "height",
            _positive_number(
                self.height,
                name="viewbox.height",
                path="scene/viewbox",
            ),
        )


# ---------------------------------------------------------------------------
# Definition references
# ---------------------------------------------------------------------------


class DefinitionKind(
    StrEnum
):
    LINEAR_GRADIENT = (
        "linear-gradient"
    )

    RADIAL_GRADIENT = (
        "radial-gradient"
    )

    PATTERN = "pattern"
    MASK = "mask"

    CLIP_PATH = (
        "clip-path"
    )

    FILTER = "filter"

    COMPONENT = (
        "component"
    )

    MARKER = "marker"


@dataclass(
    frozen=True,
    slots=True,
)
class DefinitionRef:
    target: str

    expected_kind: (
        DefinitionKind
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "target",
            _required_nonempty_text(
                self.target,
                name=(
                    "definition target"
                ),
                path=(
                    "scene/reference"
                ),
            ),
        )

        if (
            self.expected_kind
            is not None
            and not isinstance(
                self.expected_kind,
                DefinitionKind,
            )
        ):
            object.__setattr__(
                self,
                "expected_kind",
                DefinitionKind(
                    self.expected_kind
                ),
            )


# ---------------------------------------------------------------------------
# Accessibility
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class Accessibility:
    title: str | None = None

    description: (
        str
        | None
    ) = None

    role: str | None = None

    aria_label: (
        str
        | None
    ) = None

    focusable: (
        bool
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "title",
            "description",
            "role",
            "aria_label",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_nonempty_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    name=field_name,
                    path=(
                        "scene/accessibility"
                    ),
                ),
            )

        if (
            self.focusable
            is not None
            and not isinstance(
                self.focusable,
                bool,
            )
        ):
            raise SceneSchemaError(
                (
                    "focusable must be "
                    "boolean or None"
                ),
                path=(
                    "scene/accessibility"
                ),
            )


# ---------------------------------------------------------------------------
# Interaction metadata
# ---------------------------------------------------------------------------


class PointerEvents(
    StrEnum
):
    AUTO = "auto"
    NONE = "none"

    VISIBLE_PAINTED = (
        "visiblePainted"
    )

    VISIBLE_FILL = (
        "visibleFill"
    )

    VISIBLE_STROKE = (
        "visibleStroke"
    )

    VISIBLE = "visible"

    PAINTED = "painted"

    FILL = "fill"
    STROKE = "stroke"
    ALL = "all"


class HitTestPolicy(
    StrEnum
):
    FILL = "fill"
    STROKE = "stroke"

    BOUNDS = "bounds"

    EXPLICIT_PATH = (
        "explicit-path"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Interaction:
    classes: tuple[
        str,
        ...
    ] = ()

    data: Metadata = (
        EMPTY_METADATA
    )

    pointer_events: (
        PointerEvents
        | None
    ) = None

    hit_test: (
        HitTestPolicy
        | None
    ) = None

    hit_path: (
        GeometryPath
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "classes",
            _normalized_classes(
                self.classes,
                path=(
                    "scene/interaction"
                ),
            ),
        )

        if not isinstance(
            self.data,
            Metadata,
        ):
            raise SceneSchemaError(
                (
                    "interaction data "
                    "must be Metadata"
                ),
                path=(
                    "scene/interaction"
                ),
            )

        if (
            self.pointer_events
            is not None
            and not isinstance(
                self.pointer_events,
                PointerEvents,
            )
        ):
            object.__setattr__(
                self,
                "pointer_events",
                PointerEvents(
                    self.pointer_events
                ),
            )

        if (
            self.hit_test
            is not None
            and not isinstance(
                self.hit_test,
                HitTestPolicy,
            )
        ):
            object.__setattr__(
                self,
                "hit_test",
                HitTestPolicy(
                    self.hit_test
                ),
            )

        if (
            self.hit_test
            == HitTestPolicy.EXPLICIT_PATH
            and self.hit_path
            is None
        ):
            raise SceneSchemaError(
                (
                    "explicit-path hit "
                    "testing requires "
                    "hit_path"
                ),
                path=(
                    "scene/interaction"
                ),
            )


# ---------------------------------------------------------------------------
# Resource model
# ---------------------------------------------------------------------------


class ResourceKind(
    StrEnum
):
    EMBEDDED = "embedded"
    LOCAL = "local"
    EXTERNAL = "external"


@dataclass(
    frozen=True,
    slots=True,
)
class ResourceRef:
    kind: ResourceKind

    locator: str

    media_type: (
        str
        | None
    ) = None

    digest: (
        str
        | None
    ) = None

    byte_size: (
        int
        | None
    ) = None

    semantic_id: (
        str
        | None
    ) = None

    schema: str = (
        RESOURCE_SCHEMA
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            ResourceKind,
        ):
            object.__setattr__(
                self,
                "kind",
                ResourceKind(
                    self.kind
                ),
            )

        object.__setattr__(
            self,
            "locator",
            _required_nonempty_text(
                self.locator,
                name=(
                    "resource locator"
                ),
                path=(
                    "scene/resource"
                ),
            ),
        )

        for name in (
            "media_type",
            "digest",
            "semantic_id",
        ):
            object.__setattr__(
                self,
                name,
                _optional_nonempty_text(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path=(
                        "scene/resource"
                    ),
                ),
            )

        if (
            self.byte_size
            is not None
        ):
            if (
                isinstance(
                    self.byte_size,
                    bool,
                )
                or not isinstance(
                    self.byte_size,
                    int,
                )
            ):
                raise SceneSchemaError(
                    (
                        "resource byte_size "
                        "must be an integer "
                        "or None"
                    ),
                    path=(
                        "scene/resource"
                    ),
                )

            if self.byte_size < 0:
                raise SceneSchemaError(
                    (
                        "resource byte_size "
                        "must be non-negative"
                    ),
                    path=(
                        "scene/resource"
                    ),
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ResourcePolicy:
    allow_embedded: bool = True
    allow_local: bool = False
    allow_external: bool = False

    allow_data_uri: bool = False

    max_embedded_bytes: int = (
        8
        * 1024
        * 1024
    )

    allowed_media_types: tuple[
        str,
        ...
    ] = (
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/svg+xml",
    )

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "allow_embedded",
            "allow_local",
            "allow_external",
            "allow_data_uri",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                bool,
            ):
                raise ResourcePolicyError(
                    f"{name} must be boolean",
                    path=(
                        "scene/resource-policy"
                    ),
                )

        if (
            isinstance(
                self.max_embedded_bytes,
                bool,
            )
            or not isinstance(
                self.max_embedded_bytes,
                int,
            )
            or self.max_embedded_bytes
            < 0
        ):
            raise ResourcePolicyError(
                (
                    "max_embedded_bytes "
                    "must be a non-negative "
                    "integer"
                ),
                path=(
                    "scene/resource-policy"
                ),
            )

        normalized_types: list[
            str
        ] = []

        seen: set[
            str
        ] = set()

        for media_type in (
            self.allowed_media_types
        ):
            value = (
                _required_nonempty_text(
                    media_type,
                    name="media type",
                    path=(
                        "scene/resource-policy"
                    ),
                )
                .lower()
            )

            if value not in seen:
                seen.add(value)
                normalized_types.append(
                    value
                )

        object.__setattr__(
            self,
            "allowed_media_types",
            tuple(
                sorted(
                    normalized_types
                )
            ),
        )


DEFAULT_RESOURCE_POLICY: Final[
    ResourcePolicy
] = ResourcePolicy()


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------


class ColorSpace(
    StrEnum
):
    SRGB = "srgb"


@dataclass(
    frozen=True,
    slots=True,
)
class Color:
    red: float
    green: float
    blue: float
    alpha: float = 1.0

    space: ColorSpace = (
        ColorSpace.SRGB
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.space,
            ColorSpace,
        ):
            object.__setattr__(
                self,
                "space",
                ColorSpace(
                    self.space
                ),
            )

        for name in (
            "red",
            "green",
            "blue",
            "alpha",
        ):
            object.__setattr__(
                self,
                name,
                _unit_interval(
                    getattr(
                        self,
                        name,
                    ),
                    name=(
                        f"color.{name}"
                    ),
                    path="scene/color",
                ),
            )

    @classmethod
    def rgb8(
        cls,
        red: int,
        green: int,
        blue: int,
        alpha: int = 255,
    ) -> Self:
        for name, value in (
            ("red", red),
            ("green", green),
            ("blue", blue),
            ("alpha", alpha),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise SceneSchemaError(
                    (
                        f"{name} must be "
                        "an integer"
                    ),
                    path="scene/color",
                )

            if not (
                0
                <= value
                <= 255
            ):
                raise SceneSchemaError(
                    (
                        f"{name} must lie "
                        "within [0, 255]"
                    ),
                    path="scene/color",
                )

        return cls(
            red / 255.0,
            green / 255.0,
            blue / 255.0,
            alpha / 255.0,
        )

    @classmethod
    def from_hex(
        cls,
        value: str,
    ) -> Self:
        text = (
            _required_nonempty_text(
                value,
                name="hex color",
                path="scene/color",
            )
        )

        if text.startswith("#"):
            text = text[1:]

        if len(text) not in (
            3,
            4,
            6,
            8,
        ):
            raise SceneSchemaError(
                (
                    "hex color must have "
                    "3, 4, 6, or 8 "
                    "hexadecimal digits"
                ),
                path="scene/color",
            )

        if len(text) in (
            3,
            4,
        ):
            text = "".join(
                character * 2
                for character
                in text
            )

        try:
            channels = [
                int(
                    text[
                        index:
                        index + 2
                    ],
                    16,
                )
                for index
                in range(
                    0,
                    len(text),
                    2,
                )
            ]
        except ValueError as exc:
            raise SceneSchemaError(
                (
                    "hex color contains "
                    "non-hexadecimal digits"
                ),
                path="scene/color",
            ) from exc

        if len(channels) == 3:
            channels.append(
                255
            )

        return cls.rgb8(
            *channels
        )


BLACK: Final[
    Color
] = Color(
    0.0,
    0.0,
    0.0,
    1.0,
)

WHITE: Final[
    Color
] = Color(
    1.0,
    1.0,
    1.0,
    1.0,
)

TRANSPARENT: Final[
    Color
] = Color(
    0.0,
    0.0,
    0.0,
    0.0,
)


# ---------------------------------------------------------------------------
# Paint algebra
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class NoPaint:
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CurrentColorPaint:
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class SolidPaint:
    color: Color

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.color,
            Color,
        ):
            raise SceneSchemaError(
                (
                    "solid paint "
                    "requires Color"
                ),
                path="scene/paint",
            )


@dataclass(
    frozen=True,
    slots=True,
)
class DefinitionPaint:
    reference: DefinitionRef

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.reference,
            DefinitionRef,
        ):
            raise SceneSchemaError(
                (
                    "definition paint "
                    "requires DefinitionRef"
                ),
                path="scene/paint",
            )

        allowed = {
            DefinitionKind.LINEAR_GRADIENT,
            DefinitionKind.RADIAL_GRADIENT,
            DefinitionKind.PATTERN,
        }

        if (
            self.reference.expected_kind
            is not None
            and (
                self.reference.expected_kind
                not in allowed
            )
        ):
            raise SceneSchemaError(
                (
                    "definition paint must "
                    "reference a gradient "
                    "or pattern"
                ),
                path="scene/paint",
                context={
                    "expected_kind": (
                        self.reference
                        .expected_kind
                        .value
                    ),
                },
            )


Paint: TypeAlias = (
    NoPaint
    | CurrentColorPaint
    | SolidPaint
    | DefinitionPaint
)


NO_PAINT: Final[
    NoPaint
] = NoPaint()

CURRENT_COLOR: Final[
    CurrentColorPaint
] = CurrentColorPaint()

DEFAULT_FILL: Final[
    SolidPaint
] = SolidPaint(
    BLACK
)


# ---------------------------------------------------------------------------
# Style and compositing
# ---------------------------------------------------------------------------


class BlendMode(
    StrEnum
):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"

    COLOR_DODGE = (
        "color-dodge"
    )

    COLOR_BURN = (
        "color-burn"
    )

    HARD_LIGHT = (
        "hard-light"
    )

    SOFT_LIGHT = (
        "soft-light"
    )

    DIFFERENCE = (
        "difference"
    )

    EXCLUSION = (
        "exclusion"
    )

    HUE = "hue"
    SATURATION = "saturation"
    COLOR = "color"
    LUMINOSITY = "luminosity"


class Visibility(
    StrEnum
):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    COLLAPSE = "collapse"


class Display(
    StrEnum
):
    INLINE = "inline"
    NONE = "none"


class VectorEffect(
    StrEnum
):
    NONE = "none"

    NON_SCALING_STROKE = (
        "non-scaling-stroke"
    )


class PaintOrder(
    StrEnum
):
    NORMAL = "normal"

    FILL_STROKE_MARKERS = (
        "fill stroke markers"
    )

    STROKE_FILL_MARKERS = (
        "stroke fill markers"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Style:
    """
    Explicit presentation semantics.

    ``None`` means the style property is unspecified and therefore remains
    available for deterministic inheritance.

    Explicit absence of paint uses NO_PAINT rather than None.
    """

    fill: Paint | None = None

    fill_opacity: (
        float
        | None
    ) = None

    fill_rule: (
        FillRule
        | None
    ) = None

    stroke: Paint | None = None

    stroke_opacity: (
        float
        | None
    ) = None

    stroke_width: (
        float
        | None
    ) = None

    stroke_cap: (
        StrokeLineCap
        | None
    ) = None

    stroke_join: (
        StrokeLineJoin
        | None
    ) = None

    stroke_miter_limit: (
        float
        | None
    ) = None

    stroke_dasharray: (
        tuple[
            float,
            ...
        ]
        | None
    ) = None

    stroke_dashoffset: (
        float
        | None
    ) = None

    paint_order: (
        PaintOrder
        | None
    ) = None

    vector_effect: (
        VectorEffect
        | None
    ) = None

    blend_mode: (
        BlendMode
        | None
    ) = None

    visibility: (
        Visibility
        | None
    ) = None

    display: (
        Display
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        valid_paints = (
            NoPaint,
            CurrentColorPaint,
            SolidPaint,
            DefinitionPaint,
        )

        for field_name in (
            "fill",
            "stroke",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                value is not None
                and not isinstance(
                    value,
                    valid_paints,
                )
            ):
                raise SceneSchemaError(
                    (
                        f"style {field_name} "
                        "must be a typed Paint"
                    ),
                    path="scene/style",
                )

        for field_name in (
            "fill_opacity",
            "stroke_opacity",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _unit_interval(
                        value,
                        name=field_name,
                        path="scene/style",
                    ),
                )

        if (
            self.stroke_width
            is not None
        ):
            object.__setattr__(
                self,
                "stroke_width",
                _non_negative_number(
                    self.stroke_width,
                    name="stroke_width",
                    path="scene/style",
                ),
            )

        if (
            self.stroke_miter_limit
            is not None
        ):
            object.__setattr__(
                self,
                "stroke_miter_limit",
                _positive_number(
                    self.stroke_miter_limit,
                    name=(
                        "stroke_miter_limit"
                    ),
                    path="scene/style",
                ),
            )

        if (
            self.stroke_dasharray
            is not None
        ):
            dasharray = tuple(
                _non_negative_number(
                    item,
                    name=(
                        "stroke_dasharray "
                        "item"
                    ),
                    path="scene/style",
                )
                for item
                in self.stroke_dasharray
            )

            if (
                dasharray
                and all(
                    item == 0.0
                    for item
                    in dasharray
                )
            ):
                raise SceneSchemaError(
                    (
                        "stroke_dasharray "
                        "must not consist "
                        "entirely of zero "
                        "lengths"
                    ),
                    path="scene/style",
                )

            object.__setattr__(
                self,
                "stroke_dasharray",
                dasharray,
            )

        if (
            self.stroke_dashoffset
            is not None
        ):
            object.__setattr__(
                self,
                "stroke_dashoffset",
                _finite_number(
                    self.stroke_dashoffset,
                    name=(
                        "stroke_dashoffset"
                    ),
                    path="scene/style",
                ),
            )

        enum_fields = (
            (
                "fill_rule",
                FillRule,
            ),
            (
                "stroke_cap",
                StrokeLineCap,
            ),
            (
                "stroke_join",
                StrokeLineJoin,
            ),
            (
                "paint_order",
                PaintOrder,
            ),
            (
                "vector_effect",
                VectorEffect,
            ),
            (
                "blend_mode",
                BlendMode,
            ),
            (
                "visibility",
                Visibility,
            ),
            (
                "display",
                Display,
            ),
        )

        for (
            field_name,
            enum_type,
        ) in enum_fields:
            value = getattr(
                self,
                field_name,
            )

            if (
                value is not None
                and not isinstance(
                    value,
                    enum_type,
                )
            ):
                object.__setattr__(
                    self,
                    field_name,
                    enum_type(
                        value
                    ),
                )

    def overlay(
        self,
        child: (
            Style
            | None
        ),
    ) -> Style:
        """
        Resolve one explicit inherited style overlay.

        Child values replace inherited values only when explicitly specified.
        """

        if child is None:
            return self

        return Style(
            fill=(
                self.fill
                if child.fill
                is None
                else child.fill
            ),
            fill_opacity=(
                self.fill_opacity
                if child.fill_opacity
                is None
                else child.fill_opacity
            ),
            fill_rule=(
                self.fill_rule
                if child.fill_rule
                is None
                else child.fill_rule
            ),
            stroke=(
                self.stroke
                if child.stroke
                is None
                else child.stroke
            ),
            stroke_opacity=(
                self.stroke_opacity
                if child.stroke_opacity
                is None
                else child.stroke_opacity
            ),
            stroke_width=(
                self.stroke_width
                if child.stroke_width
                is None
                else child.stroke_width
            ),
            stroke_cap=(
                self.stroke_cap
                if child.stroke_cap
                is None
                else child.stroke_cap
            ),
            stroke_join=(
                self.stroke_join
                if child.stroke_join
                is None
                else child.stroke_join
            ),
            stroke_miter_limit=(
                self.stroke_miter_limit
                if child.stroke_miter_limit
                is None
                else child.stroke_miter_limit
            ),
            stroke_dasharray=(
                self.stroke_dasharray
                if child.stroke_dasharray
                is None
                else child.stroke_dasharray
            ),
            stroke_dashoffset=(
                self.stroke_dashoffset
                if child.stroke_dashoffset
                is None
                else child.stroke_dashoffset
            ),
            paint_order=(
                self.paint_order
                if child.paint_order
                is None
                else child.paint_order
            ),
            vector_effect=(
                self.vector_effect
                if child.vector_effect
                is None
                else child.vector_effect
            ),
            blend_mode=(
                self.blend_mode
                if child.blend_mode
                is None
                else child.blend_mode
            ),
            visibility=(
                self.visibility
                if child.visibility
                is None
                else child.visibility
            ),
            display=(
                self.display
                if child.display
                is None
                else child.display
            ),
        )


EMPTY_STYLE: Final[
    Style
] = Style()


class StyleInheritance(
    StrEnum
):
    INHERIT = "inherit"
    ISOLATE = "isolate"


# ---------------------------------------------------------------------------
# Gradient foundations
# ---------------------------------------------------------------------------


class CoordinateUnits(
    StrEnum
):
    USER_SPACE_ON_USE = (
        "userSpaceOnUse"
    )

    OBJECT_BOUNDING_BOX = (
        "objectBoundingBox"
    )


class SpreadMethod(
    StrEnum
):
    PAD = "pad"
    REFLECT = "reflect"
    REPEAT = "repeat"


class ColorInterpolation(
    StrEnum
):
    SRGB = "sRGB"

    LINEAR_RGB = (
        "linearRGB"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class GradientStop:
    offset: float
    color: Color
    opacity: float = 1.0

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "offset",
            _unit_interval(
                self.offset,
                name=(
                    "gradient stop "
                    "offset"
                ),
                path=(
                    "scene/gradient-stop"
                ),
            ),
        )

        if not isinstance(
            self.color,
            Color,
        ):
            raise SceneSchemaError(
                (
                    "gradient stop color "
                    "must be Color"
                ),
                path=(
                    "scene/gradient-stop"
                ),
            )

        object.__setattr__(
            self,
            "opacity",
            _unit_interval(
                self.opacity,
                name=(
                    "gradient stop "
                    "opacity"
                ),
                path=(
                    "scene/gradient-stop"
                ),
            ),
        )


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------


class FontStyle(
    StrEnum
):
    NORMAL = "normal"
    ITALIC = "italic"
    OBLIQUE = "oblique"


class FontStretch(
    StrEnum
):
    ULTRA_CONDENSED = (
        "ultra-condensed"
    )

    EXTRA_CONDENSED = (
        "extra-condensed"
    )

    CONDENSED = (
        "condensed"
    )

    SEMI_CONDENSED = (
        "semi-condensed"
    )

    NORMAL = "normal"

    SEMI_EXPANDED = (
        "semi-expanded"
    )

    EXPANDED = (
        "expanded"
    )

    EXTRA_EXPANDED = (
        "extra-expanded"
    )

    ULTRA_EXPANDED = (
        "ultra-expanded"
    )


class TextAnchor(
    StrEnum
):
    START = "start"
    MIDDLE = "middle"
    END = "end"


class TextDirection(
    StrEnum
):
    LTR = "ltr"
    RTL = "rtl"
    AUTO = "auto"


class WritingMode(
    StrEnum
):
    HORIZONTAL_TB = (
        "horizontal-tb"
    )

    VERTICAL_RL = (
        "vertical-rl"
    )

    VERTICAL_LR = (
        "vertical-lr"
    )


class BaselinePolicy(
    StrEnum
):
    AUTO = "auto"

    ALPHABETIC = (
        "alphabetic"
    )

    CENTRAL = "central"
    MIDDLE = "middle"
    HANGING = "hanging"

    TEXT_BEFORE_EDGE = (
        "text-before-edge"
    )

    TEXT_AFTER_EDGE = (
        "text-after-edge"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Typography:
    font_families: tuple[
        str,
        ...
    ] = ()

    font_size: (
        float
        | None
    ) = None

    font_weight: (
        int
        | str
        | None
    ) = None

    font_style: (
        FontStyle
        | None
    ) = None

    font_stretch: (
        FontStretch
        | None
    ) = None

    letter_spacing: (
        float
        | None
    ) = None

    word_spacing: (
        float
        | None
    ) = None

    text_anchor: (
        TextAnchor
        | None
    ) = None

    baseline: (
        BaselinePolicy
        | None
    ) = None

    direction: (
        TextDirection
        | None
    ) = None

    writing_mode: (
        WritingMode
        | None
    ) = None

    language: (
        str
        | None
    ) = None

    script: (
        str
        | None
    ) = None

    features: tuple[
        str,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        families: list[
            str
        ] = []

        for family in (
            self.font_families
        ):
            normalized = (
                _required_nonempty_text(
                    family,
                    name="font family",
                    path=(
                        "scene/typography"
                    ),
                )
            )

            if (
                normalized
                not in families
            ):
                families.append(
                    normalized
                )

        object.__setattr__(
            self,
            "font_families",
            tuple(families),
        )

        if (
            self.font_size
            is not None
        ):
            object.__setattr__(
                self,
                "font_size",
                _positive_number(
                    self.font_size,
                    name="font_size",
                    path=(
                        "scene/typography"
                    ),
                ),
            )

        if (
            self.font_weight
            is not None
        ):
            weight = (
                self.font_weight
            )

            if isinstance(
                weight,
                bool,
            ):
                raise SceneSchemaError(
                    (
                        "font_weight must "
                        "not be boolean"
                    ),
                    path=(
                        "scene/typography"
                    ),
                )

            if isinstance(
                weight,
                int,
            ):
                if not (
                    1
                    <= weight
                    <= 1000
                ):
                    raise SceneSchemaError(
                        (
                            "numeric font_weight "
                            "must lie within "
                            "[1, 1000]"
                        ),
                        path=(
                            "scene/typography"
                        ),
                    )

            elif isinstance(
                weight,
                str,
            ):
                object.__setattr__(
                    self,
                    "font_weight",
                    _required_nonempty_text(
                        weight,
                        name="font_weight",
                        path=(
                            "scene/typography"
                        ),
                    ),
                )

            else:
                raise SceneSchemaError(
                    (
                        "font_weight must be "
                        "integer, string, or None"
                    ),
                    path=(
                        "scene/typography"
                    ),
                )

        for field_name in (
            "letter_spacing",
            "word_spacing",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _finite_number(
                        value,
                        name=field_name,
                        path=(
                            "scene/typography"
                        ),
                    ),
                )

        enum_fields = (
            (
                "font_style",
                FontStyle,
            ),
            (
                "font_stretch",
                FontStretch,
            ),
            (
                "text_anchor",
                TextAnchor,
            ),
            (
                "baseline",
                BaselinePolicy,
            ),
            (
                "direction",
                TextDirection,
            ),
            (
                "writing_mode",
                WritingMode,
            ),
        )

        for (
            field_name,
            enum_type,
        ) in enum_fields:
            value = getattr(
                self,
                field_name,
            )

            if (
                value is not None
                and not isinstance(
                    value,
                    enum_type,
                )
            ):
                object.__setattr__(
                    self,
                    field_name,
                    enum_type(
                        value
                    ),
                )

        for field_name in (
            "language",
            "script",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_nonempty_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    name=field_name,
                    path=(
                        "scene/typography"
                    ),
                ),
            )

        features: list[
            str
        ] = []

        for feature in (
            self.features
        ):
            normalized = (
                _required_nonempty_text(
                    feature,
                    name=(
                        "font feature"
                    ),
                    path=(
                        "scene/typography"
                    ),
                )
            )

            if (
                normalized
                not in features
            ):
                features.append(
                    normalized
                )

        object.__setattr__(
            self,
            "features",
            tuple(features),
        )


# ---------------------------------------------------------------------------
# Node protocol
# ---------------------------------------------------------------------------


class NodeType(
    StrEnum
):
    GROUP = "group"
    PATH = "path"
    RECT = "rect"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    LINE = "line"
    POLYLINE = "polyline"
    POLYGON = "polygon"
    TEXT = "text"

    TEXT_PATH = (
        "text-path"
    )

    IMAGE = "image"
    INSTANCE = "instance"


@runtime_checkable
class NodeProtocol(
    Protocol
):
    node_type: ClassVar[
        NodeType
    ]

    semantic_id: (
        str
        | None
    )

    name: (
        str
        | None
    )

    metadata: Metadata

    transform: (
        AffineTransform
    )

    style: (
        Style
        | None
    )

    visible: bool

    opacity: float

    clip: (
        DefinitionRef
        | None
    )

    mask: (
        DefinitionRef
        | None
    )

    filter: (
        DefinitionRef
        | None
    )

    accessibility: (
        Accessibility
        | None
    )

    interaction: (
        Interaction
        | None
    )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class NodeBase:
    semantic_id: (
        str
        | None
    ) = None

    name: (
        str
        | None
    ) = None

    metadata: Metadata = (
        EMPTY_METADATA
    )

    transform: AffineTransform = (
        IDENTITY_TRANSFORM
    )

    style: (
        Style
        | None
    ) = None

    visible: bool = True

    opacity: float = 1.0

    clip: (
        DefinitionRef
        | None
    ) = None

    mask: (
        DefinitionRef
        | None
    ) = None

    filter: (
        DefinitionRef
        | None
    ) = None

    accessibility: (
        Accessibility
        | None
    ) = None

    interaction: (
        Interaction
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "semantic_id",
            _optional_nonempty_text(
                self.semantic_id,
                name="semantic_id",
                path="scene/node",
            ),
        )

        object.__setattr__(
            self,
            "name",
            _optional_nonempty_text(
                self.name,
                name="name",
                path="scene/node",
            ),
        )

        if not isinstance(
            self.metadata,
            Metadata,
        ):
            raise SceneSchemaError(
                (
                    "node metadata must "
                    "be Metadata"
                ),
                path="scene/node",
            )

        if not isinstance(
            self.transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "node transform must "
                    "be AffineTransform"
                ),
                path="scene/node",
            )

        if (
            self.style
            is not None
            and not isinstance(
                self.style,
                Style,
            )
        ):
            raise SceneSchemaError(
                (
                    "node style must be "
                    "Style or None"
                ),
                path="scene/node",
            )

        if not isinstance(
            self.visible,
            bool,
        ):
            raise SceneSchemaError(
                (
                    "node visible must "
                    "be boolean"
                ),
                path="scene/node",
            )

        object.__setattr__(
            self,
            "opacity",
            _unit_interval(
                self.opacity,
                name=(
                    "node opacity"
                ),
                path="scene/node",
            ),
        )

        for (
            field_name,
            expected_kind,
        ) in (
            (
                "clip",
                DefinitionKind.CLIP_PATH,
            ),
            (
                "mask",
                DefinitionKind.MASK,
            ),
            (
                "filter",
                DefinitionKind.FILTER,
            ),
        ):
            reference = getattr(
                self,
                field_name,
            )

            if reference is None:
                continue

            if not isinstance(
                reference,
                DefinitionRef,
            ):
                raise SceneSchemaError(
                    (
                        f"node {field_name} "
                        "must be DefinitionRef "
                        "or None"
                    ),
                    path="scene/node",
                )

            if (
                reference.expected_kind
                is not None
                and (
                    reference.expected_kind
                    != expected_kind
                )
            ):
                raise SceneSchemaError(
                    (
                        f"node {field_name} "
                        "reference has "
                        "incompatible "
                        "expected kind"
                    ),
                    path="scene/node",
                )

        if (
            self.accessibility
            is not None
            and not isinstance(
                self.accessibility,
                Accessibility,
            )
        ):
            raise SceneSchemaError(
                (
                    "node accessibility "
                    "must be Accessibility "
                    "or None"
                ),
                path="scene/node",
            )

        if (
            self.interaction
            is not None
            and not isinstance(
                self.interaction,
                Interaction,
            )
        ):
            raise SceneSchemaError(
                (
                    "node interaction "
                    "must be Interaction "
                    "or None"
                ),
                path="scene/node",
            )


# ---------------------------------------------------------------------------
# Core semantic node families
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Group(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.GROUP

    children: tuple[
        Node,
        ...
    ] = ()

    style_inheritance: (
        StyleInheritance
    ) = StyleInheritance.INHERIT

    isolation: bool = False

    layer: (
        str
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        super(
            Group,
            self,
        ).__post_init__()

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        for child in (
            self.children
        ):
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "group children "
                        "must be canonical "
                        "nodes"
                    ),
                    path="scene/group",
                    context={
                        "received_type": (
                            type(
                                child
                            ).__name__
                        ),
                    },
                )

        if not isinstance(
            self.style_inheritance,
            StyleInheritance,
        ):
            object.__setattr__(
                self,
                "style_inheritance",
                StyleInheritance(
                    self.style_inheritance
                ),
            )

        if not isinstance(
            self.isolation,
            bool,
        ):
            raise SceneSchemaError(
                (
                    "group isolation must "
                    "be boolean"
                ),
                path="scene/group",
            )

        object.__setattr__(
            self,
            "layer",
            _optional_nonempty_text(
                self.layer,
                name="layer",
                path="scene/group",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class PathNode(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.PATH

    path: GeometryPath

    marker_start: (
        DefinitionRef
        | None
    ) = None

    marker_mid: (
        DefinitionRef
        | None
    ) = None

    marker_end: (
        DefinitionRef
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        super(
            PathNode,
            self,
        ).__post_init__()

        if not isinstance(
            self.path,
            GeometryPath,
        ):
            raise SceneSchemaError(
                (
                    "PathNode path must "
                    "be geometry.Path"
                ),
                path="scene/path",
            )

        for field_name in (
            "marker_start",
            "marker_mid",
            "marker_end",
        ):
            reference = getattr(
                self,
                field_name,
            )

            if reference is None:
                continue

            if not isinstance(
                reference,
                DefinitionRef,
            ):
                raise SceneSchemaError(
                    (
                        f"{field_name} must "
                        "be DefinitionRef "
                        "or None"
                    ),
                    path="scene/path",
                )

            if (
                reference.expected_kind
                is not None
                and (
                    reference.expected_kind
                    != DefinitionKind.MARKER
                )
            ):
                raise SceneSchemaError(
                    (
                        f"{field_name} must "
                        "reference a marker"
                    ),
                    path="scene/path",
                )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Rect(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.RECT

    x: float = 0.0
    y: float = 0.0

    width: float
    height: float

    rx: float = 0.0
    ry: float = 0.0

    def __post_init__(
        self,
    ) -> None:
        super(
            Rect,
            self,
        ).__post_init__()

        for name in (
            "x",
            "y",
        ):
            object.__setattr__(
                self,
                name,
                _finite_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path="scene/rect",
                ),
            )

        for name in (
            "width",
            "height",
            "rx",
            "ry",
        ):
            object.__setattr__(
                self,
                name,
                _non_negative_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path="scene/rect",
                ),
            )

        if (
            self.width > 0.0
            and self.rx
            > self.width / 2.0
        ):
            object.__setattr__(
                self,
                "rx",
                self.width / 2.0,
            )

        if (
            self.height > 0.0
            and self.ry
            > self.height / 2.0
        ):
            object.__setattr__(
                self,
                "ry",
                self.height / 2.0,
            )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Circle(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.CIRCLE

    center: Point
    radius: float

    def __post_init__(
        self,
    ) -> None:
        super(
            Circle,
            self,
        ).__post_init__()

        if not isinstance(
            self.center,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "circle center must "
                    "be Point"
                ),
                path="scene/circle",
            )

        object.__setattr__(
            self,
            "radius",
            _non_negative_number(
                self.radius,
                name="radius",
                path="scene/circle",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Ellipse(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.ELLIPSE

    center: Point
    rx: float
    ry: float

    def __post_init__(
        self,
    ) -> None:
        super(
            Ellipse,
            self,
        ).__post_init__()

        if not isinstance(
            self.center,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "ellipse center must "
                    "be Point"
                ),
                path="scene/ellipse",
            )

        for name in (
            "rx",
            "ry",
        ):
            object.__setattr__(
                self,
                name,
                _non_negative_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path="scene/ellipse",
                ),
            )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Line(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.LINE

    start: Point
    end: Point

    def __post_init__(
        self,
    ) -> None:
        super(
            Line,
            self,
        ).__post_init__()

        if (
            not isinstance(
                self.start,
                Point,
            )
            or not isinstance(
                self.end,
                Point,
            )
        ):
            raise SceneSchemaError(
                (
                    "line start and end "
                    "must be Point values"
                ),
                path="scene/line",
            )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Polyline(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.POLYLINE

    points: tuple[
        Point,
        ...
    ]

    def __post_init__(
        self,
    ) -> None:
        super(
            Polyline,
            self,
        ).__post_init__()

        object.__setattr__(
            self,
            "points",
            tuple(
                self.points
            ),
        )

        for point in self.points:
            if not isinstance(
                point,
                Point,
            ):
                raise SceneSchemaError(
                    (
                        "polyline points "
                        "must be Point values"
                    ),
                    path=(
                        "scene/polyline"
                    ),
                )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Polygon(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.POLYGON

    points: tuple[
        Point,
        ...
    ]

    def __post_init__(
        self,
    ) -> None:
        super(
            Polygon,
            self,
        ).__post_init__()

        object.__setattr__(
            self,
            "points",
            tuple(
                self.points
            ),
        )

        for point in self.points:
            if not isinstance(
                point,
                Point,
            ):
                raise SceneSchemaError(
                    (
                        "polygon points "
                        "must be Point values"
                    ),
                    path=(
                        "scene/polygon"
                    ),
                )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Text(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.TEXT

    content: str

    position: Point = Point(
        0.0,
        0.0,
    )

    typography: Typography = (
        Typography()
    )

    def __post_init__(
        self,
    ) -> None:
        super(
            Text,
            self,
        ).__post_init__()

        if not isinstance(
            self.content,
            str,
        ):
            raise SceneSchemaError(
                (
                    "text content must "
                    "be Unicode string"
                ),
                path="scene/text",
            )

        if "\x00" in self.content:
            raise SceneSchemaError(
                (
                    "text content must "
                    "not contain NUL "
                    "characters"
                ),
                path="scene/text",
            )

        if not isinstance(
            self.position,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "text position must "
                    "be Point"
                ),
                path="scene/text",
            )

        if not isinstance(
            self.typography,
            Typography,
        ):
            raise SceneSchemaError(
                (
                    "text typography "
                    "must be Typography"
                ),
                path="scene/text",
            )


class TextPathMethod(
    StrEnum
):
    ALIGN = "align"
    STRETCH = "stretch"


class TextPathSpacing(
    StrEnum
):
    AUTO = "auto"
    EXACT = "exact"


class TextPathSide(
    StrEnum
):
    LEFT = "left"
    RIGHT = "right"


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class TextPath(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.TEXT_PATH

    content: str
    path_ref: str

    start_offset: float = 0.0

    offset_is_percent: bool = (
        False
    )

    method: TextPathMethod = (
        TextPathMethod.ALIGN
    )

    spacing: TextPathSpacing = (
        TextPathSpacing.AUTO
    )

    side: TextPathSide = (
        TextPathSide.LEFT
    )

    typography: Typography = (
        Typography()
    )

    def __post_init__(
        self,
    ) -> None:
        super(
            TextPath,
            self,
        ).__post_init__()

        if (
            not isinstance(
                self.content,
                str,
            )
            or "\x00"
            in self.content
        ):
            raise SceneSchemaError(
                (
                    "text-path content "
                    "must be valid Unicode "
                    "text without NUL"
                ),
                path=(
                    "scene/text-path"
                ),
            )

        object.__setattr__(
            self,
            "path_ref",
            _required_nonempty_text(
                self.path_ref,
                name=(
                    "text-path reference"
                ),
                path=(
                    "scene/text-path"
                ),
            ),
        )

        object.__setattr__(
            self,
            "start_offset",
            _finite_number(
                self.start_offset,
                name="start_offset",
                path=(
                    "scene/text-path"
                ),
            ),
        )

        if not isinstance(
            self.offset_is_percent,
            bool,
        ):
            raise SceneSchemaError(
                (
                    "offset_is_percent "
                    "must be boolean"
                ),
                path=(
                    "scene/text-path"
                ),
            )

        for (
            field_name,
            enum_type,
        ) in (
            (
                "method",
                TextPathMethod,
            ),
            (
                "spacing",
                TextPathSpacing,
            ),
            (
                "side",
                TextPathSide,
            ),
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                enum_type,
            ):
                object.__setattr__(
                    self,
                    field_name,
                    enum_type(
                        value
                    ),
                )

        if not isinstance(
            self.typography,
            Typography,
        ):
            raise SceneSchemaError(
                (
                    "text-path typography "
                    "must be Typography"
                ),
                path=(
                    "scene/text-path"
                ),
            )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Image(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.IMAGE

    source: ResourceRef

    x: float = 0.0
    y: float = 0.0

    width: float
    height: float

    preserve_aspect_ratio: (
        PreserveAspectRatio
    ) = PreserveAspectRatio()

    def __post_init__(
        self,
    ) -> None:
        super(
            Image,
            self,
        ).__post_init__()

        if not isinstance(
            self.source,
            ResourceRef,
        ):
            raise SceneSchemaError(
                (
                    "image source must "
                    "be ResourceRef"
                ),
                path="scene/image",
            )

        for name in (
            "x",
            "y",
        ):
            object.__setattr__(
                self,
                name,
                _finite_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path="scene/image",
                ),
            )

        for name in (
            "width",
            "height",
        ):
            object.__setattr__(
                self,
                name,
                _non_negative_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path="scene/image",
                ),
            )

        if not isinstance(
            self.preserve_aspect_ratio,
            PreserveAspectRatio,
        ):
            raise SceneSchemaError(
                (
                    "image "
                    "preserve_aspect_ratio "
                    "must be "
                    "PreserveAspectRatio"
                ),
                path="scene/image",
            )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Instance(
    NodeBase
):
    node_type: ClassVar[
        NodeType
    ] = NodeType.INSTANCE

    component: DefinitionRef

    position: Point = Point(
        0.0,
        0.0,
    )

    scale_x: float = 1.0
    scale_y: float = 1.0

    rotation: float = 0.0

    style_override: (
        Style
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        super(
            Instance,
            self,
        ).__post_init__()

        if not isinstance(
            self.component,
            DefinitionRef,
        ):
            raise SceneSchemaError(
                (
                    "instance component "
                    "must be DefinitionRef"
                ),
                path=(
                    "scene/instance"
                ),
            )

        if (
            self.component.expected_kind
            is not None
            and (
                self.component.expected_kind
                != DefinitionKind.COMPONENT
            )
        ):
            raise SceneSchemaError(
                (
                    "instance component "
                    "reference must target "
                    "component kind"
                ),
                path=(
                    "scene/instance"
                ),
            )

        if not isinstance(
            self.position,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "instance position "
                    "must be Point"
                ),
                path=(
                    "scene/instance"
                ),
            )

        for name in (
            "scale_x",
            "scale_y",
            "rotation",
        ):
            object.__setattr__(
                self,
                name,
                _finite_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path=(
                        "scene/instance"
                    ),
                ),
            )

        if (
            self.style_override
            is not None
            and not isinstance(
                self.style_override,
                Style,
            )
        ):
            raise SceneSchemaError(
                (
                    "instance style_override "
                    "must be Style or None"
                ),
                path=(
                    "scene/instance"
                ),
            )

    def instance_transform(
        self,
    ) -> AffineTransform:
        return (
            AffineTransform.translate(
                self.position.x,
                self.position.y,
            )
            @ AffineTransform.rotate(
                self.rotation
            )
            @ AffineTransform.scale(
                self.scale_x,
                self.scale_y,
            )
            @ self.transform
        )


Node: TypeAlias = (
    Group
    | PathNode
    | Rect
    | Circle
    | Ellipse
    | Line
    | Polyline
    | Polygon
    | Text
    | TextPath
    | Image
    | Instance
)


NODE_TYPES: Final[
    tuple[
        type[NodeBase],
        ...
    ]
] = (
    Group,
    PathNode,
    Rect,
    Circle,
    Ellipse,
    Line,
    Polyline,
    Polygon,
    Text,
    TextPath,
    Image,
    Instance,
)


def is_node(
    value: object,
) -> bool:
    return isinstance(
        value,
        NODE_TYPES,
    )


# ---------------------------------------------------------------------------
# Reusable definition base
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class DefinitionBase:
    semantic_id: str

    name: (
        str
        | None
    ) = None

    metadata: Metadata = (
        EMPTY_METADATA
    )

    definition_kind: ClassVar[
        DefinitionKind
    ]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "semantic_id",
            _required_nonempty_text(
                self.semantic_id,
                name=(
                    "definition "
                    "semantic_id"
                ),
                path=(
                    "scene/definition"
                ),
            ),
        )

        object.__setattr__(
            self,
            "name",
            _optional_nonempty_text(
                self.name,
                name=(
                    "definition name"
                ),
                path=(
                    "scene/definition"
                ),
            ),
        )

        if not isinstance(
            self.metadata,
            Metadata,
        ):
            raise SceneSchemaError(
                (
                    "definition metadata "
                    "must be Metadata"
                ),
                path=(
                    "scene/definition"
                ),
            )

    @property
    def ref(
        self,
    ) -> DefinitionRef:
        return DefinitionRef(
            target=(
                self.semantic_id
            ),
            expected_kind=(
                self.definition_kind
            ),
        )


# ---------------------------------------------------------------------------
# Gradient definitions
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class LinearGradient(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = (
        DefinitionKind
        .LINEAR_GRADIENT
    )

    start: Point = Point(
        0.0,
        0.0,
    )

    end: Point = Point(
        1.0,
        0.0,
    )

    units: CoordinateUnits = (
        CoordinateUnits
        .OBJECT_BOUNDING_BOX
    )

    transform: AffineTransform = (
        IDENTITY_TRANSFORM
    )

    spread: SpreadMethod = (
        SpreadMethod.PAD
    )

    interpolation: (
        ColorInterpolation
    ) = (
        ColorInterpolation.SRGB
    )

    stops: tuple[
        GradientStop,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            LinearGradient,
            self,
        ).__post_init__()

        if (
            not isinstance(
                self.start,
                Point,
            )
            or not isinstance(
                self.end,
                Point,
            )
        ):
            raise SceneSchemaError(
                (
                    "linear gradient "
                    "start/end must be "
                    "Point values"
                ),
                path=(
                    "scene/linear-gradient"
                ),
            )

        if not isinstance(
            self.units,
            CoordinateUnits,
        ):
            object.__setattr__(
                self,
                "units",
                CoordinateUnits(
                    self.units
                ),
            )

        if not isinstance(
            self.transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "linear gradient "
                    "transform must be "
                    "AffineTransform"
                ),
                path=(
                    "scene/linear-gradient"
                ),
            )

        if not isinstance(
            self.spread,
            SpreadMethod,
        ):
            object.__setattr__(
                self,
                "spread",
                SpreadMethod(
                    self.spread
                ),
            )

        if not isinstance(
            self.interpolation,
            ColorInterpolation,
        ):
            object.__setattr__(
                self,
                "interpolation",
                ColorInterpolation(
                    self.interpolation
                ),
            )

        object.__setattr__(
            self,
            "stops",
            tuple(
                self.stops
            ),
        )

        for stop in self.stops:
            if not isinstance(
                stop,
                GradientStop,
            ):
                raise SceneSchemaError(
                    (
                        "linear gradient "
                        "stops must be "
                        "GradientStop values"
                    ),
                    path=(
                        "scene/linear-gradient"
                    ),
                )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class RadialGradient(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = (
        DefinitionKind
        .RADIAL_GRADIENT
    )

    center: Point = Point(
        0.5,
        0.5,
    )

    radius: float = 0.5

    focal_point: (
        Point
        | None
    ) = None

    focal_radius: float = 0.0

    units: CoordinateUnits = (
        CoordinateUnits
        .OBJECT_BOUNDING_BOX
    )

    transform: AffineTransform = (
        IDENTITY_TRANSFORM
    )

    spread: SpreadMethod = (
        SpreadMethod.PAD
    )

    interpolation: (
        ColorInterpolation
    ) = (
        ColorInterpolation.SRGB
    )

    stops: tuple[
        GradientStop,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            RadialGradient,
            self,
        ).__post_init__()

        if not isinstance(
            self.center,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "radial gradient "
                    "center must be Point"
                ),
                path=(
                    "scene/radial-gradient"
                ),
            )

        if (
            self.focal_point
            is not None
            and not isinstance(
                self.focal_point,
                Point,
            )
        ):
            raise SceneSchemaError(
                (
                    "radial gradient "
                    "focal_point must be "
                    "Point or None"
                ),
                path=(
                    "scene/radial-gradient"
                ),
            )

        object.__setattr__(
            self,
            "radius",
            _positive_number(
                self.radius,
                name="radius",
                path=(
                    "scene/radial-gradient"
                ),
            ),
        )

        object.__setattr__(
            self,
            "focal_radius",
            _non_negative_number(
                self.focal_radius,
                name=(
                    "focal_radius"
                ),
                path=(
                    "scene/radial-gradient"
                ),
            ),
        )

        if (
            self.focal_radius
            > self.radius
        ):
            raise SceneSchemaError(
                (
                    "radial gradient "
                    "focal_radius must not "
                    "exceed radius"
                ),
                path=(
                    "scene/radial-gradient"
                ),
            )

        if not isinstance(
            self.units,
            CoordinateUnits,
        ):
            object.__setattr__(
                self,
                "units",
                CoordinateUnits(
                    self.units
                ),
            )

        if not isinstance(
            self.transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "radial gradient "
                    "transform must be "
                    "AffineTransform"
                ),
                path=(
                    "scene/radial-gradient"
                ),
            )

        if not isinstance(
            self.spread,
            SpreadMethod,
        ):
            object.__setattr__(
                self,
                "spread",
                SpreadMethod(
                    self.spread
                ),
            )

        if not isinstance(
            self.interpolation,
            ColorInterpolation,
        ):
            object.__setattr__(
                self,
                "interpolation",
                ColorInterpolation(
                    self.interpolation
                ),
            )

        object.__setattr__(
            self,
            "stops",
            tuple(
                self.stops
            ),
        )

        for stop in self.stops:
            if not isinstance(
                stop,
                GradientStop,
            ):
                raise SceneSchemaError(
                    (
                        "radial gradient "
                        "stops must be "
                        "GradientStop values"
                    ),
                    path=(
                        "scene/radial-gradient"
                    ),
                )


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Pattern(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = (
        DefinitionKind.PATTERN
    )

    x: float = 0.0
    y: float = 0.0

    width: float
    height: float

    units: CoordinateUnits = (
        CoordinateUnits
        .OBJECT_BOUNDING_BOX
    )

    content_units: CoordinateUnits = (
        CoordinateUnits
        .USER_SPACE_ON_USE
    )

    transform: AffineTransform = (
        IDENTITY_TRANSFORM
    )

    view_box: (
        ViewBox
        | None
    ) = None

    preserve_aspect_ratio: (
        PreserveAspectRatio
    ) = PreserveAspectRatio()

    children: tuple[
        Node,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            Pattern,
            self,
        ).__post_init__()

        for name in (
            "x",
            "y",
        ):
            object.__setattr__(
                self,
                name,
                _finite_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path=(
                        "scene/pattern"
                    ),
                ),
            )

        for name in (
            "width",
            "height",
        ):
            object.__setattr__(
                self,
                name,
                _positive_number(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    path=(
                        "scene/pattern"
                    ),
                ),
            )

        for field_name in (
            "units",
            "content_units",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                CoordinateUnits,
            ):
                object.__setattr__(
                    self,
                    field_name,
                    CoordinateUnits(
                        value
                    ),
                )

        if not isinstance(
            self.transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "pattern transform "
                    "must be "
                    "AffineTransform"
                ),
                path=(
                    "scene/pattern"
                ),
            )

        if (
            self.view_box
            is not None
            and not isinstance(
                self.view_box,
                ViewBox,
            )
        ):
            raise SceneSchemaError(
                (
                    "pattern view_box "
                    "must be ViewBox "
                    "or None"
                ),
                path=(
                    "scene/pattern"
                ),
            )

        if not isinstance(
            self.preserve_aspect_ratio,
            PreserveAspectRatio,
        ):
            raise SceneSchemaError(
                (
                    "pattern "
                    "preserve_aspect_ratio "
                    "must be "
                    "PreserveAspectRatio"
                ),
                path=(
                    "scene/pattern"
                ),
            )

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        for child in self.children:
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "pattern children "
                        "must be canonical "
                        "nodes"
                    ),
                    path=(
                        "scene/pattern"
                    ),
                )


# ---------------------------------------------------------------------------
# Masks
# ---------------------------------------------------------------------------


class MaskMode(
    StrEnum
):
    ALPHA = "alpha"
    LUMINANCE = "luminance"


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Mask(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = DefinitionKind.MASK

    mode: MaskMode = (
        MaskMode.LUMINANCE
    )

    units: CoordinateUnits = (
        CoordinateUnits
        .OBJECT_BOUNDING_BOX
    )

    content_units: CoordinateUnits = (
        CoordinateUnits
        .USER_SPACE_ON_USE
    )

    x: (
        float
        | None
    ) = None

    y: (
        float
        | None
    ) = None

    width: (
        float
        | None
    ) = None

    height: (
        float
        | None
    ) = None

    transform: AffineTransform = (
        IDENTITY_TRANSFORM
    )

    children: tuple[
        Node,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            Mask,
            self,
        ).__post_init__()

        if not isinstance(
            self.mode,
            MaskMode,
        ):
            object.__setattr__(
                self,
                "mode",
                MaskMode(
                    self.mode
                ),
            )

        for field_name in (
            "units",
            "content_units",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                CoordinateUnits,
            ):
                object.__setattr__(
                    self,
                    field_name,
                    CoordinateUnits(
                        value
                    ),
                )

        for name in (
            "x",
            "y",
        ):
            value = getattr(
                self,
                name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _finite_number(
                        value,
                        name=name,
                        path="scene/mask",
                    ),
                )

        for name in (
            "width",
            "height",
        ):
            value = getattr(
                self,
                name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _positive_number(
                        value,
                        name=name,
                        path="scene/mask",
                    ),
                )

        if not isinstance(
            self.transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "mask transform must "
                    "be AffineTransform"
                ),
                path="scene/mask",
            )

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        for child in self.children:
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "mask children must "
                        "be canonical nodes"
                    ),
                    path="scene/mask",
                )


# ---------------------------------------------------------------------------
# Clip paths
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ClipPath(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = (
        DefinitionKind.CLIP_PATH
    )

    units: CoordinateUnits = (
        CoordinateUnits
        .USER_SPACE_ON_USE
    )

    transform: AffineTransform = (
        IDENTITY_TRANSFORM
    )

    children: tuple[
        Node,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            ClipPath,
            self,
        ).__post_init__()

        if not isinstance(
            self.units,
            CoordinateUnits,
        ):
            object.__setattr__(
                self,
                "units",
                CoordinateUnits(
                    self.units
                ),
            )

        if not isinstance(
            self.transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "clip-path transform "
                    "must be "
                    "AffineTransform"
                ),
                path=(
                    "scene/clip-path"
                ),
            )

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        for child in self.children:
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "clip-path children "
                        "must be canonical "
                        "nodes"
                    ),
                    path=(
                        "scene/clip-path"
                    ),
                )


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------


class MarkerUnits(
    StrEnum
):
    STROKE_WIDTH = (
        "strokeWidth"
    )

    USER_SPACE_ON_USE = (
        "userSpaceOnUse"
    )


class MarkerOrient(
    StrEnum
):
    AUTO = "auto"

    AUTO_START_REVERSE = (
        "auto-start-reverse"
    )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Marker(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = DefinitionKind.MARKER

    ref_point: Point = Point(
        0.0,
        0.0,
    )

    width: float = 3.0
    height: float = 3.0

    units: MarkerUnits = (
        MarkerUnits.STROKE_WIDTH
    )

    orient: (
        MarkerOrient
        | float
    ) = MarkerOrient.AUTO

    view_box: (
        ViewBox
        | None
    ) = None

    preserve_aspect_ratio: (
        PreserveAspectRatio
    ) = PreserveAspectRatio()

    children: tuple[
        Node,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            Marker,
            self,
        ).__post_init__()

        if not isinstance(
            self.ref_point,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "marker ref_point "
                    "must be Point"
                ),
                path="scene/marker",
            )

        object.__setattr__(
            self,
            "width",
            _positive_number(
                self.width,
                name=(
                    "marker width"
                ),
                path="scene/marker",
            ),
        )

        object.__setattr__(
            self,
            "height",
            _positive_number(
                self.height,
                name=(
                    "marker height"
                ),
                path="scene/marker",
            ),
        )

        if not isinstance(
            self.units,
            MarkerUnits,
        ):
            object.__setattr__(
                self,
                "units",
                MarkerUnits(
                    self.units
                ),
            )

        if isinstance(
            self.orient,
            str,
        ):
            try:
                object.__setattr__(
                    self,
                    "orient",
                    MarkerOrient(
                        self.orient
                    ),
                )

            except ValueError:
                try:
                    numeric_orient = (
                        float(
                            self.orient
                        )
                    )
                except ValueError as exc:
                    raise SceneSchemaError(
                        (
                            "marker orient "
                            "must be auto, "
                            "auto-start-reverse, "
                            "or a finite angle"
                        ),
                        path=(
                            "scene/marker"
                        ),
                    ) from exc

                object.__setattr__(
                    self,
                    "orient",
                    _finite_number(
                        numeric_orient,
                        name=(
                            "marker orient"
                        ),
                        path=(
                            "scene/marker"
                        ),
                    ),
                )

        elif not isinstance(
            self.orient,
            MarkerOrient,
        ):
            object.__setattr__(
                self,
                "orient",
                _finite_number(
                    self.orient,
                    name=(
                        "marker orient"
                    ),
                    path="scene/marker",
                ),
            )

        if (
            self.view_box
            is not None
            and not isinstance(
                self.view_box,
                ViewBox,
            )
        ):
            raise SceneSchemaError(
                (
                    "marker view_box "
                    "must be ViewBox "
                    "or None"
                ),
                path="scene/marker",
            )

        if not isinstance(
            self.preserve_aspect_ratio,
            PreserveAspectRatio,
        ):
            raise SceneSchemaError(
                (
                    "marker "
                    "preserve_aspect_ratio "
                    "must be "
                    "PreserveAspectRatio"
                ),
                path="scene/marker",
            )

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        for child in self.children:
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "marker children "
                        "must be canonical "
                        "nodes"
                    ),
                    path="scene/marker",
                )


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class Anchor:
    name: str
    point: Point

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "name",
            _required_nonempty_text(
                self.name,
                name=(
                    "anchor name"
                ),
                path=(
                    "scene/component/"
                    "anchor"
                ),
            ),
        )

        if not isinstance(
            self.point,
            Point,
        ):
            raise SceneSchemaError(
                (
                    "component anchor "
                    "point must be Point"
                ),
                path=(
                    "scene/component/"
                    "anchor"
                ),
            )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Component(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = (
        DefinitionKind.COMPONENT
    )

    view_box: (
        ViewBox
        | None
    ) = None

    preserve_aspect_ratio: (
        PreserveAspectRatio
    ) = PreserveAspectRatio()

    anchors: tuple[
        Anchor,
        ...
    ] = ()

    style_slots: tuple[
        str,
        ...
    ] = ()

    children: tuple[
        Node,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        super(
            Component,
            self,
        ).__post_init__()

        if (
            self.view_box
            is not None
            and not isinstance(
                self.view_box,
                ViewBox,
            )
        ):
            raise SceneSchemaError(
                (
                    "component view_box "
                    "must be ViewBox "
                    "or None"
                ),
                path=(
                    "scene/component"
                ),
            )

        if not isinstance(
            self.preserve_aspect_ratio,
            PreserveAspectRatio,
        ):
            raise SceneSchemaError(
                (
                    "component "
                    "preserve_aspect_ratio "
                    "must be "
                    "PreserveAspectRatio"
                ),
                path=(
                    "scene/component"
                ),
            )

        object.__setattr__(
            self,
            "anchors",
            tuple(
                self.anchors
            ),
        )

        names: set[
            str
        ] = set()

        for anchor in self.anchors:
            if not isinstance(
                anchor,
                Anchor,
            ):
                raise SceneSchemaError(
                    (
                        "component anchors "
                        "must be Anchor values"
                    ),
                    path=(
                        "scene/component"
                    ),
                )

            if (
                anchor.name
                in names
            ):
                raise SceneSchemaError(
                    (
                        "component anchor "
                        "names must be unique"
                    ),
                    path=(
                        "scene/component"
                    ),
                    context={
                        "anchor": (
                            anchor.name
                        ),
                    },
                )

            names.add(
                anchor.name
            )

        slots: list[
            str
        ] = []

        for slot in (
            self.style_slots
        ):
            normalized = (
                _required_nonempty_text(
                    slot,
                    name="style slot",
                    path=(
                        "scene/component"
                    ),
                )
            )

            if (
                normalized
                not in slots
            ):
                slots.append(
                    normalized
                )

        object.__setattr__(
            self,
            "style_slots",
            tuple(
                slots
            ),
        )

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        for child in self.children:
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "component children "
                        "must be canonical "
                        "nodes"
                    ),
                    path=(
                        "scene/component"
                    ),
                )


# ---------------------------------------------------------------------------
# Filter graph
# ---------------------------------------------------------------------------


class FilterPrimitiveType(
    StrEnum
):
    GAUSSIAN_BLUR = (
        "gaussian-blur"
    )

    OFFSET = "offset"
    FLOOD = "flood"
    BLEND = "blend"

    COMPOSITE = (
        "composite"
    )

    COLOR_MATRIX = (
        "color-matrix"
    )

    COMPONENT_TRANSFER = (
        "component-transfer"
    )

    MORPHOLOGY = (
        "morphology"
    )

    TURBULENCE = (
        "turbulence"
    )

    DISPLACEMENT_MAP = (
        "displacement-map"
    )

    CONVOLUTION_MATRIX = (
        "convolution-matrix"
    )

    DIFFUSE_LIGHTING = (
        "diffuse-lighting"
    )

    SPECULAR_LIGHTING = (
        "specular-lighting"
    )

    MERGE = "merge"
    TILE = "tile"
    IMAGE = "image"

    DROP_SHADOW = (
        "drop-shadow"
    )


class StandardFilterInput(
    StrEnum
):
    SOURCE_GRAPHIC = (
        "SourceGraphic"
    )

    SOURCE_ALPHA = (
        "SourceAlpha"
    )

    BACKGROUND_IMAGE = (
        "BackgroundImage"
    )

    BACKGROUND_ALPHA = (
        "BackgroundAlpha"
    )

    FILL_PAINT = (
        "FillPaint"
    )

    STROKE_PAINT = (
        "StrokePaint"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FilterInput:
    standard: (
        StandardFilterInput
        | None
    ) = None

    result: (
        str
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.standard
            is not None
            and not isinstance(
                self.standard,
                StandardFilterInput,
            )
        ):
            object.__setattr__(
                self,
                "standard",
                StandardFilterInput(
                    self.standard
                ),
            )

        object.__setattr__(
            self,
            "result",
            _optional_nonempty_text(
                self.result,
                name=(
                    "filter result input"
                ),
                path=(
                    "scene/filter/input"
                ),
            ),
        )

        if (
            (
                self.standard
                is None
            )
            ==
            (
                self.result
                is None
            )
        ):
            raise SceneSchemaError(
                (
                    "filter input must "
                    "specify exactly one "
                    "standard source or "
                    "named result"
                ),
                path=(
                    "scene/filter/input"
                ),
            )

    @classmethod
    def source(
        cls,
        value: StandardFilterInput,
    ) -> Self:
        return cls(
            standard=value
        )

    @classmethod
    def named(
        cls,
        result: str,
    ) -> Self:
        return cls(
            result=result
        )


FilterParameterValue: TypeAlias = (
    str
    | int
    | float
    | bool
    | Color
    | ResourceRef
)


@dataclass(
    frozen=True,
    slots=True,
    order=True,
)
class FilterParameter:
    name: str

    value: (
        FilterParameterValue
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "name",
            _required_nonempty_text(
                self.name,
                name=(
                    "filter parameter name"
                ),
                path=(
                    "scene/filter/"
                    "parameter"
                ),
            ),
        )

        value = self.value

        if (
            isinstance(
                value,
                float,
            )
            and not math.isfinite(
                value
            )
        ):
            raise SceneSchemaError(
                (
                    "filter parameter "
                    "float must be finite"
                ),
                path=(
                    "scene/filter/"
                    "parameter"
                ),
                context={
                    "parameter": (
                        self.name
                    ),
                },
            )

        if not isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
                Color,
                ResourceRef,
            ),
        ):
            raise SceneSchemaError(
                (
                    "unsupported filter "
                    "parameter value type"
                ),
                path=(
                    "scene/filter/"
                    "parameter"
                ),
                context={
                    "parameter": (
                        self.name
                    ),
                    "received_type": (
                        type(
                            value
                        ).__name__
                    ),
                },
            )


@dataclass(
    frozen=True,
    slots=True,
)
class FilterPrimitive:
    primitive_type: (
        FilterPrimitiveType
    )

    inputs: tuple[
        FilterInput,
        ...
    ] = ()

    parameters: tuple[
        FilterParameter,
        ...
    ] = ()

    result: (
        str
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.primitive_type,
            FilterPrimitiveType,
        ):
            object.__setattr__(
                self,
                "primitive_type",
                FilterPrimitiveType(
                    self.primitive_type
                ),
            )

        object.__setattr__(
            self,
            "inputs",
            tuple(
                self.inputs
            ),
        )

        object.__setattr__(
            self,
            "parameters",
            tuple(
                self.parameters
            ),
        )

        for item in self.inputs:
            if not isinstance(
                item,
                FilterInput,
            ):
                raise SceneSchemaError(
                    (
                        "filter primitive "
                        "inputs must be "
                        "FilterInput values"
                    ),
                    path=(
                        "scene/filter/"
                        "primitive"
                    ),
                )

        parameters: dict[
            str,
            FilterParameter,
        ] = {}

        for parameter in (
            self.parameters
        ):
            if not isinstance(
                parameter,
                FilterParameter,
            ):
                raise SceneSchemaError(
                    (
                        "filter primitive "
                        "parameters must be "
                        "FilterParameter "
                        "values"
                    ),
                    path=(
                        "scene/filter/"
                        "primitive"
                    ),
                )

            if (
                parameter.name
                in parameters
            ):
                raise SceneSchemaError(
                    (
                        "filter primitive "
                        "parameter names "
                        "must be unique"
                    ),
                    path=(
                        "scene/filter/"
                        "primitive"
                    ),
                    context={
                        "parameter": (
                            parameter.name
                        ),
                    },
                )

            parameters[
                parameter.name
            ] = parameter

        object.__setattr__(
            self,
            "parameters",
            tuple(
                parameters[name]
                for name
                in sorted(
                    parameters
                )
            ),
        )

        object.__setattr__(
            self,
            "result",
            _optional_nonempty_text(
                self.result,
                name=(
                    "filter result"
                ),
                path=(
                    "scene/filter/"
                    "primitive"
                ),
            ),
        )

    @classmethod
    def build(
        cls,
        primitive_type: (
            FilterPrimitiveType
        ),
        *,
        inputs: Sequence[
            FilterInput
        ] = (),
        parameters: (
            Mapping[
                str,
                FilterParameterValue,
            ]
            | None
        ) = None,
        result: (
            str
            | None
        ) = None,
    ) -> Self:
        return cls(
            primitive_type=(
                primitive_type
            ),
            inputs=tuple(
                inputs
            ),
            parameters=tuple(
                FilterParameter(
                    name,
                    value,
                )
                for name, value
                in (
                    parameters
                    or {}
                ).items()
            ),
            result=result,
        )

    def parameter(
        self,
        name: str,
    ) -> (
        FilterParameterValue
        | None
    ):
        for parameter in (
            self.parameters
        ):
            if (
                parameter.name
                == name
            ):
                return (
                    parameter.value
                )

        return None


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class FilterGraph(
    DefinitionBase
):
    definition_kind: ClassVar[
        DefinitionKind
    ] = (
        DefinitionKind.FILTER
    )

    primitives: tuple[
        FilterPrimitive,
        ...
    ] = ()

    units: CoordinateUnits = (
        CoordinateUnits
        .OBJECT_BOUNDING_BOX
    )

    primitive_units: (
        CoordinateUnits
    ) = (
        CoordinateUnits
        .USER_SPACE_ON_USE
    )

    x: (
        float
        | None
    ) = None

    y: (
        float
        | None
    ) = None

    width: (
        float
        | None
    ) = None

    height: (
        float
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        super(
            FilterGraph,
            self,
        ).__post_init__()

        object.__setattr__(
            self,
            "primitives",
            tuple(
                self.primitives
            ),
        )

        for primitive in (
            self.primitives
        ):
            if not isinstance(
                primitive,
                FilterPrimitive,
            ):
                raise SceneSchemaError(
                    (
                        "filter graph "
                        "primitives must be "
                        "FilterPrimitive "
                        "values"
                    ),
                    path=(
                        "scene/filter"
                    ),
                )

        for field_name in (
            "units",
            "primitive_units",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                CoordinateUnits,
            ):
                object.__setattr__(
                    self,
                    field_name,
                    CoordinateUnits(
                        value
                    ),
                )

        for name in (
            "x",
            "y",
        ):
            value = getattr(
                self,
                name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _finite_number(
                        value,
                        name=name,
                        path=(
                            "scene/filter"
                        ),
                    ),
                )

        for name in (
            "width",
            "height",
        ):
            value = getattr(
                self,
                name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _positive_number(
                        value,
                        name=name,
                        path=(
                            "scene/filter"
                        ),
                    ),
                )


# ---------------------------------------------------------------------------
# Definition union
# ---------------------------------------------------------------------------


Definition: TypeAlias = (
    LinearGradient
    | RadialGradient
    | Pattern
    | Mask
    | ClipPath
    | FilterGraph
    | Component
    | Marker
)


DEFINITION_TYPES: Final[
    tuple[
        type[
            DefinitionBase
        ],
        ...
    ]
] = (
    LinearGradient,
    RadialGradient,
    Pattern,
    Mask,
    ClipPath,
    FilterGraph,
    Component,
    Marker,
)


def is_definition(
    value: object,
) -> bool:
    return isinstance(
        value,
        DEFINITION_TYPES,
    )


# ---------------------------------------------------------------------------
# Scene compilation hints
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class SceneCompilationHints:
    compatibility_profile: str = (
        "modern-svg"
    )

    readable_output: bool = (
        False
    )

    preserve_components: bool = (
        True
    )

    preserve_primitives: bool = (
        True
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "compatibility_profile",
            _required_nonempty_text(
                self.compatibility_profile,
                name=(
                    "compatibility_profile"
                ),
                path=(
                    "scene/"
                    "compilation-hints"
                ),
            ),
        )

        for name in (
            "readable_output",
            "preserve_components",
            "preserve_primitives",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                bool,
            ):
                raise SceneSchemaError(
                    (
                        f"{name} must "
                        "be boolean"
                    ),
                    path=(
                        "scene/"
                        "compilation-hints"
                    ),
                )


DEFAULT_COMPILATION_HINTS: Final[
    SceneCompilationHints
] = SceneCompilationHints()


# ---------------------------------------------------------------------------
# Root scene
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class Scene:
    semantic_id: (
        str
        | None
    ) = None

    name: (
        str
        | None
    ) = None

    width: (
        float
        | None
    ) = None

    height: (
        float
        | None
    ) = None

    view_box: (
        ViewBox
        | None
    ) = None

    coordinate_space: (
        CoordinateSpacePolicy
    ) = (
        CoordinateSpacePolicy
        .SVG_Y_DOWN
    )

    preserve_aspect_ratio: (
        PreserveAspectRatio
    ) = PreserveAspectRatio()

    root_transform: (
        AffineTransform
    ) = IDENTITY_TRANSFORM

    children: tuple[
        Node,
        ...
    ] = ()

    definitions: tuple[
        Definition,
        ...
    ] = ()

    metadata: Metadata = (
        EMPTY_METADATA
    )

    accessibility: (
        Accessibility
        | None
    ) = None

    resource_policy: (
        ResourcePolicy
    ) = (
        DEFAULT_RESOURCE_POLICY
    )

    compilation_hints: (
        SceneCompilationHints
    ) = (
        DEFAULT_COMPILATION_HINTS
    )

    schema: str = (
        SCENE_SCHEMA
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "semantic_id",
            _optional_nonempty_text(
                self.semantic_id,
                name=(
                    "scene semantic_id"
                ),
                path="scene",
            ),
        )

        object.__setattr__(
            self,
            "name",
            _optional_nonempty_text(
                self.name,
                name="scene name",
                path="scene",
            ),
        )

        for name in (
            "width",
            "height",
        ):
            value = getattr(
                self,
                name,
            )

            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _positive_number(
                        value,
                        name=name,
                        path="scene",
                    ),
                )

        if (
            self.view_box
            is not None
            and not isinstance(
                self.view_box,
                ViewBox,
            )
        ):
            raise SceneSchemaError(
                (
                    "scene view_box "
                    "must be ViewBox "
                    "or None"
                ),
                path="scene",
            )

        if not isinstance(
            self.coordinate_space,
            CoordinateSpacePolicy,
        ):
            object.__setattr__(
                self,
                "coordinate_space",
                CoordinateSpacePolicy(
                    self.coordinate_space
                ),
            )

        if not isinstance(
            self.preserve_aspect_ratio,
            PreserveAspectRatio,
        ):
            raise SceneSchemaError(
                (
                    "scene "
                    "preserve_aspect_ratio "
                    "must be "
                    "PreserveAspectRatio"
                ),
                path="scene",
            )

        if not isinstance(
            self.root_transform,
            AffineTransform,
        ):
            raise SceneSchemaError(
                (
                    "scene root_transform "
                    "must be "
                    "AffineTransform"
                ),
                path="scene",
            )

        object.__setattr__(
            self,
            "children",
            tuple(
                self.children
            ),
        )

        object.__setattr__(
            self,
            "definitions",
            tuple(
                self.definitions
            ),
        )

        for child in self.children:
            if not is_node(
                child
            ):
                raise SceneSchemaError(
                    (
                        "scene children "
                        "must be canonical "
                        "nodes"
                    ),
                    path="scene",
                    context={
                        "received_type": (
                            type(
                                child
                            ).__name__
                        ),
                    },
                )

        for definition in (
            self.definitions
        ):
            if not is_definition(
                definition
            ):
                raise SceneSchemaError(
                    (
                        "scene definitions "
                        "must be canonical "
                        "definitions"
                    ),
                    path="scene",
                    context={
                        "received_type": (
                            type(
                                definition
                            ).__name__
                        ),
                    },
                )

        if not isinstance(
            self.metadata,
            Metadata,
        ):
            raise SceneSchemaError(
                (
                    "scene metadata must "
                    "be Metadata"
                ),
                path="scene",
            )

        if (
            self.accessibility
            is not None
            and not isinstance(
                self.accessibility,
                Accessibility,
            )
        ):
            raise SceneSchemaError(
                (
                    "scene accessibility "
                    "must be Accessibility "
                    "or None"
                ),
                path="scene",
            )

        if not isinstance(
            self.resource_policy,
            ResourcePolicy,
        ):
            raise SceneSchemaError(
                (
                    "scene resource_policy "
                    "must be ResourcePolicy"
                ),
                path="scene",
            )

        if not isinstance(
            self.compilation_hints,
            SceneCompilationHints,
        ):
            raise SceneSchemaError(
                (
                    "scene "
                    "compilation_hints "
                    "must be "
                    "SceneCompilationHints"
                ),
                path="scene",
            )

    @property
    def definition_count(
        self,
    ) -> int:
        return len(
            self.definitions
        )

    @property
    def root_child_count(
        self,
    ) -> int:
        return len(
            self.children
        )


# ---------------------------------------------------------------------------
# Deterministic traversal
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class NodeVisit:
    node: Node
    path: str
    depth: int

    definition_id: (
        str
        | None
    ) = None


@dataclass(
    frozen=True,
    slots=True,
)
class DefinitionVisit:
    definition: Definition
    path: str


def node_children(
    node: Node,
) -> tuple[
    Node,
    ...
]:
    if isinstance(
        node,
        Group,
    ):
        return (
            node.children
        )

    return ()


def definition_children(
    definition: Definition,
) -> tuple[
    Node,
    ...
]:
    if isinstance(
        definition,
        (
            Pattern,
            Mask,
            ClipPath,
            Component,
            Marker,
        ),
    ):
        return (
            definition.children
        )

    return ()


def walk_nodes(
    nodes: Sequence[
        Node
    ],
    *,
    path_prefix: str = (
        "scene/root"
    ),
    start_depth: int = 0,
    definition_id: (
        str
        | None
    ) = None,
) -> Iterator[
    NodeVisit
]:
    """
    Depth-first deterministic canonical traversal.

    Instances remain instances. Components are never expanded here.
    """

    def visit(
        node: Node,
        path: str,
        depth: int,
    ) -> Iterator[
        NodeVisit
    ]:
        yield NodeVisit(
            node=node,
            path=path,
            depth=depth,
            definition_id=(
                definition_id
            ),
        )

        children = (
            node_children(
                node
            )
        )

        for (
            index,
            child,
        ) in enumerate(
            children
        ):
            child_path = (
                f"{path}/"
                f"{child.node_type.value}"
                f"[{index}]"
            )

            yield from visit(
                child,
                child_path,
                depth + 1,
            )

    for (
        index,
        node,
    ) in enumerate(
        nodes
    ):
        path = (
            f"{path_prefix}/"
            f"{node.node_type.value}"
            f"[{index}]"
        )

        yield from visit(
            node,
            path,
            start_depth,
        )


def walk_scene_nodes(
    scene: Scene,
    *,
    include_definition_content: bool = (
        False
    ),
) -> Iterator[
    NodeVisit
]:
    yield from walk_nodes(
        scene.children
    )

    if not (
        include_definition_content
    ):
        return

    for definition in (
        scene.definitions
    ):
        children = (
            definition_children(
                definition
            )
        )

        if not children:
            continue

        prefix = (
            "scene/definitions/"
            f"{definition.definition_kind.value}"
            f"[{definition.semantic_id}]"
        )

        yield from walk_nodes(
            children,
            path_prefix=prefix,
            definition_id=(
                definition.semantic_id
            ),
        )


def walk_definitions(
    scene: Scene,
) -> Iterator[
    DefinitionVisit
]:
    for (
        index,
        definition,
    ) in enumerate(
        scene.definitions
    ):
        yield DefinitionVisit(
            definition=definition,
            path=(
                "scene/definitions/"
                f"{definition.definition_kind.value}"
                f"[{index}]"
            ),
        )


def collect_semantic_ids(
    scene: Scene,
    *,
    include_definition_content: bool = (
        True
    ),
) -> tuple[
    str,
    ...
]:
    values: list[
        str
    ] = []

    if (
        scene.semantic_id
        is not None
    ):
        values.append(
            scene.semantic_id
        )

    for definition in (
        scene.definitions
    ):
        values.append(
            definition.semantic_id
        )

    for visit in (
        walk_scene_nodes(
            scene,
            include_definition_content=(
                include_definition_content
            ),
        )
    ):
        if (
            visit.node.semantic_id
            is not None
        ):
            values.append(
                visit.node.semantic_id
            )

    return tuple(
        values
    )


def find_definition(
    scene: Scene,
    semantic_id: str,
) -> (
    Definition
    | None
):
    target = (
        _required_nonempty_text(
            semantic_id,
            name=(
                "definition semantic_id"
            ),
            path=(
                "scene/reference"
            ),
        )
    )

    for definition in (
        scene.definitions
    ):
        if (
            definition.semantic_id
            == target
        ):
            return definition

    return None


# ---------------------------------------------------------------------------
# Definition reference extraction
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class ReferenceUse:
    reference: DefinitionRef
    owner_path: str
    relation: str


def _node_paints(
    node: Node,
) -> tuple[
    Paint,
    ...
]:
    styles: list[
        Style
    ] = []

    if (
        node.style
        is not None
    ):
        styles.append(
            node.style
        )

    if (
        isinstance(
            node,
            Instance,
        )
        and (
            node.style_override
            is not None
        )
    ):
        styles.append(
            node.style_override
        )

    paints: list[
        Paint
    ] = []

    for style in styles:
        if (
            style.fill
            is not None
        ):
            paints.append(
                style.fill
            )

        if (
            style.stroke
            is not None
        ):
            paints.append(
                style.stroke
            )

    return tuple(
        paints
    )


def _common_node_references(
    node: Node,
    path: str,
) -> Iterator[
    ReferenceUse
]:
    for field_name in (
        "clip",
        "mask",
        "filter",
    ):
        reference = getattr(
            node,
            field_name,
        )

        if (
            reference
            is not None
        ):
            yield ReferenceUse(
                reference=reference,
                owner_path=path,
                relation=field_name,
            )

    if isinstance(
        node,
        PathNode,
    ):
        for field_name in (
            "marker_start",
            "marker_mid",
            "marker_end",
        ):
            reference = getattr(
                node,
                field_name,
            )

            if (
                reference
                is not None
            ):
                yield ReferenceUse(
                    reference=(
                        reference
                    ),
                    owner_path=path,
                    relation=(
                        field_name
                    ),
                )

    if isinstance(
        node,
        Instance,
    ):
        yield ReferenceUse(
            reference=(
                node.component
            ),
            owner_path=path,
            relation="component",
        )

    for paint in (
        _node_paints(
            node
        )
    ):
        if isinstance(
            paint,
            DefinitionPaint,
        ):
            yield ReferenceUse(
                reference=(
                    paint.reference
                ),
                owner_path=path,
                relation="paint",
            )


def iter_reference_uses(
    scene: Scene,
) -> Iterator[
    ReferenceUse
]:
    for visit in (
        walk_scene_nodes(
            scene,
            include_definition_content=True,
        )
    ):
        yield from (
            _common_node_references(
                visit.node,
                visit.path,
            )
        )


# ---------------------------------------------------------------------------
# Explicit style inheritance projection
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedNodeStyle:
    node: Node
    path: str
    style: Style


def walk_resolved_styles(
    nodes: Sequence[
        Node
    ],
    *,
    inherited: Style = (
        EMPTY_STYLE
    ),
    path_prefix: str = (
        "scene/root"
    ),
) -> Iterator[
    ResolvedNodeStyle
]:
    """
    Resolve semantic style inheritance deterministically.

    Group ISOLATE resets inherited style for descendants.

    Node opacity remains a separate compositing property and is intentionally
    not multiplied into style during this operation.
    """

    def visit(
        node: Node,
        path: str,
        inherited_style: Style,
    ) -> Iterator[
        ResolvedNodeStyle
    ]:
        effective = (
            inherited_style.overlay(
                node.style
            )
        )

        yield ResolvedNodeStyle(
            node=node,
            path=path,
            style=effective,
        )

        if not isinstance(
            node,
            Group,
        ):
            return

        if (
            node.style_inheritance
            == StyleInheritance.ISOLATE
        ):
            child_base = (
                EMPTY_STYLE
            )
        else:
            child_base = (
                effective
            )

        for (
            index,
            child,
        ) in enumerate(
            node.children
        ):
            child_path = (
                f"{path}/"
                f"{child.node_type.value}"
                f"[{index}]"
            )

            yield from visit(
                child,
                child_path,
                child_base,
            )

    for (
        index,
        node,
    ) in enumerate(
        nodes
    ):
        path = (
            f"{path_prefix}/"
            f"{node.node_type.value}"
            f"[{index}]"
        )

        yield from visit(
            node,
            path,
            inherited,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


__all__ = [
    "MODEL_SCHEMA",
    "SCENE_SCHEMA",
    "RESOURCE_SCHEMA",
    "MODULE_VERSION",

    "MetadataScalar",
    "MetadataEntry",
    "Metadata",
    "EMPTY_METADATA",

    "CoordinateSpacePolicy",
    "PreserveAspectAlign",
    "MeetOrSlice",
    "PreserveAspectRatio",
    "ViewBox",

    "DefinitionKind",
    "DefinitionRef",

    "Accessibility",
    "PointerEvents",
    "HitTestPolicy",
    "Interaction",

    "ResourceKind",
    "ResourceRef",
    "ResourcePolicy",
    "DEFAULT_RESOURCE_POLICY",

    "ColorSpace",
    "Color",
    "BLACK",
    "WHITE",
    "TRANSPARENT",

    "NoPaint",
    "CurrentColorPaint",
    "SolidPaint",
    "DefinitionPaint",
    "Paint",
    "NO_PAINT",
    "CURRENT_COLOR",
    "DEFAULT_FILL",

    "BlendMode",
    "Visibility",
    "Display",
    "VectorEffect",
    "PaintOrder",
    "Style",
    "EMPTY_STYLE",
    "StyleInheritance",

    "CoordinateUnits",
    "SpreadMethod",
    "ColorInterpolation",
    "GradientStop",

    "FontStyle",
    "FontStretch",
    "TextAnchor",
    "TextDirection",
    "WritingMode",
    "BaselinePolicy",
    "Typography",

    "NodeType",
    "NodeProtocol",
    "NodeBase",

    "Group",
    "PathNode",
    "Rect",
    "Circle",
    "Ellipse",
    "Line",
    "Polyline",
    "Polygon",
    "Text",

    "TextPathMethod",
    "TextPathSpacing",
    "TextPathSide",
    "TextPath",

    "Image",
    "Instance",

    "Node",
    "NODE_TYPES",
    "is_node",

    "DefinitionBase",

    "LinearGradient",
    "RadialGradient",
    "Pattern",

    "MaskMode",
    "Mask",

    "ClipPath",

    "MarkerUnits",
    "MarkerOrient",
    "Marker",

    "Anchor",
    "Component",

    "FilterPrimitiveType",
    "StandardFilterInput",
    "FilterInput",
    "FilterParameterValue",
    "FilterParameter",
    "FilterPrimitive",
    "FilterGraph",

    "Definition",
    "DEFINITION_TYPES",
    "is_definition",

    "SceneCompilationHints",
    "DEFAULT_COMPILATION_HINTS",

    "Scene",

    "NodeVisit",
    "DefinitionVisit",

    "node_children",
    "definition_children",

    "walk_nodes",
    "walk_scene_nodes",
    "walk_definitions",

    "collect_semantic_ids",
    "find_definition",

    "ReferenceUse",
    "iter_reference_uses",

    "ResolvedNodeStyle",
    "walk_resolved_styles",
]
