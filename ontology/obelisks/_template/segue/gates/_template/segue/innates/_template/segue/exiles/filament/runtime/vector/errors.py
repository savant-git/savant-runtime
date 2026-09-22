"""
SAVANT Filament Vector Renderer
Typed diagnostics and failure taxonomy.

This module defines the single canonical diagnostic and exception model
for the Filament-owned vector scene compiler.

Design requirements:

* diagnostics identify semantic scene locations rather than opaque parser
  positions whenever possible;
* validation failures are machine-readable and deterministic;
* structured warnings are first-class evidence but never hide correctness
  failures;
* semantic failures are distinguished from retryable external-resource
  failures;
* security, resource-budget, compatibility, backend, persistence, and
  serialization failures have explicit types;
* exception objects do not mutate canonical scene state;
* diagnostic serialization is stable enough to participate in compilation
  receipts and deterministic proof output;
* the module has no third-party dependencies.

The canonical vector scene remains authoritative substance. Diagnostics,
warnings, exception messages, receipts, and serialized projections are
derived evidence.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
import json
import math
from types import MappingProxyType
from typing import Any, ClassVar, Final, Self


# ---------------------------------------------------------------------------
# Public module identity
# ---------------------------------------------------------------------------

DIAGNOSTIC_SCHEMA: Final[str] = (
    "savant://filament/vector/diagnostic/1.0.0"
)

DIAGNOSTIC_REPORT_SCHEMA: Final[str] = (
    "savant://filament/vector/diagnostic-report/1.0.0"
)

ERROR_SCHEMA: Final[str] = (
    "savant://filament/vector/error/1.0.0"
)

MODULE_VERSION: Final[str] = "1.0.0"


# ---------------------------------------------------------------------------
# Diagnostic primitives
# ---------------------------------------------------------------------------


class DiagnosticSeverity(IntEnum):
    """
    Ordered diagnostic severity.

    The integer ordering is intentional so reports can deterministically
    calculate their highest observed severity without maintaining a second
    ranking table.
    """

    INFO = 10
    WARNING = 20
    ERROR = 30
    FATAL = 40

    @property
    def label(self) -> str:
        return self.name.lower()


class DiagnosticCategory(StrEnum):
    """
    Broad machine-readable diagnostic categories.

    Individual diagnostic ``code`` values remain more specific. Categories
    make it possible for callers to aggregate families of diagnostics
    without parsing human-readable messages.
    """

    CONSTRUCTION = "construction"
    VALIDATION = "validation"
    GEOMETRY = "geometry"
    TRANSFORM = "transform"
    REFERENCE = "reference"
    DEPENDENCY = "dependency"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    FILTER = "filter"
    COMPATIBILITY = "compatibility"
    SECURITY = "security"
    SERIALIZATION = "serialization"
    BACKEND = "backend"
    PERSISTENCE = "persistence"
    BUDGET = "budget"
    SCHEMA = "schema"
    CACHE = "cache"
    EXTERNAL = "external"
    INTERNAL = "internal"


class RetryDisposition(StrEnum):
    """
    Retry semantics attached to a failure or diagnostic.

    Pure semantic/compiler failures should normally be ``never``.

    External resource or provider failures may be retryable where their
    failure mode is transient.
    """

    NEVER = "never"
    RETRYABLE = "retryable"
    UNKNOWN = "unknown"


class DiagnosticPathError(ValueError):
    """Raised when a semantic diagnostic path itself is malformed."""


@dataclass(frozen=True, slots=True, order=True)
class DiagnosticPath:
    """
    Immutable semantic location within a vector scene or compiler operation.

    Example::

        scene/root/group[logo]/mask[cutout]/path[3]

    Diagnostic paths are deliberately semantic. They are not filesystem
    paths and must never be used as filesystem destinations.

    The class accepts an already-rendered canonical path but also provides
    helpers for deterministic path construction.
    """

    value: str = "scene"

    def __post_init__(self) -> None:
        normalized = self._normalize(self.value)
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _normalize(value: str) -> str:
        if not isinstance(value, str):
            raise DiagnosticPathError(
                "diagnostic path must be a string"
            )

        value = value.strip()

        if not value:
            raise DiagnosticPathError(
                "diagnostic path must not be empty"
            )

        if "\x00" in value:
            raise DiagnosticPathError(
                "diagnostic path must not contain NUL characters"
            )

        # Diagnostic paths are slash-separated semantic paths.
        # Collapse accidental repeated separators while retaining the
        # human-readable scene edifice.
        parts = [
            part.strip()
            for part in value.split("/")
            if part.strip()
        ]

        if not parts:
            raise DiagnosticPathError(
                "diagnostic path contains no semantic segments"
            )

        for part in parts:
            if "\n" in part or "\r" in part:
                raise DiagnosticPathError(
                    "diagnostic path segments must be single-line"
                )

        return "/".join(parts)

    @classmethod
    def root(cls) -> Self:
        return cls("scene")

    def child(
        self,
        kind: str,
        identity: str | int | None = None,
    ) -> Self:
        """
        Append one semantic child.

        Examples::

            DiagnosticPath.root().child("root")
            -> scene/root

            .child("group", "logo")
            -> scene/root/group[logo]

            .child("path", 3)
            -> scene/root/group[logo]/path[3]
        """

        kind = self._sanitize_segment(kind, label="kind")

        if identity is None:
            segment = kind
        else:
            identity_text = self._sanitize_segment(
                str(identity),
                label="identity",
            )
            segment = f"{kind}[{identity_text}]"

        return type(self)(f"{self.value}/{segment}")

    def indexed(
        self,
        kind: str,
        index: int,
    ) -> Self:
        if not isinstance(index, int):
            raise DiagnosticPathError(
                "diagnostic path index must be an integer"
            )

        if index < 0:
            raise DiagnosticPathError(
                "diagnostic path index must be non-negative"
            )

        return self.child(kind, index)

    @staticmethod
    def _sanitize_segment(
        value: str,
        *,
        label: str,
    ) -> str:
        if not isinstance(value, str):
            raise DiagnosticPathError(
                f"diagnostic path {label} must be a string"
            )

        value = value.strip()

        if not value:
            raise DiagnosticPathError(
                f"diagnostic path {label} must not be empty"
            )

        forbidden = {
            "/",
            "\x00",
            "\n",
            "\r",
        }

        if any(token in value for token in forbidden):
            raise DiagnosticPathError(
                f"diagnostic path {label} contains "
                "forbidden characters"
            )

        return value

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Diagnostic metadata normalization
# ---------------------------------------------------------------------------


def _normalize_scalar(value: object) -> object:
    """
    Normalize a diagnostic metadata scalar.

    Metadata exists for machine-readable evidence and must therefore avoid
    arbitrary objects with unstable repr() output.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                "diagnostic metadata floats must be finite"
            )
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, StrEnum):
        return str(value)

    if isinstance(value, IntEnum):
        return int(value)

    if isinstance(value, DiagnosticPath):
        return value.value

    raise TypeError(
        "diagnostic metadata values must be deterministic "
        f"scalar values, got {type(value).__name__}"
    )


def _freeze_context(
    context: Mapping[str, object] | None,
) -> Mapping[str, object]:
    """
    Copy and freeze diagnostic metadata.

    Keys are sorted during serialization, so insertion order never becomes
    semantic.
    """

    if context is None:
        return MappingProxyType({})

    if not isinstance(context, Mapping):
        raise TypeError(
            "diagnostic context must be a mapping"
        )

    normalized: dict[str, object] = {}

    for raw_key, raw_value in context.items():
        if not isinstance(raw_key, str):
            raise TypeError(
                "diagnostic context keys must be strings"
            )

        key = raw_key.strip()

        if not key:
            raise ValueError(
                "diagnostic context keys must not be empty"
            )

        normalized[key] = _normalize_scalar(raw_value)

    return MappingProxyType(normalized)


# ---------------------------------------------------------------------------
# Related diagnostic locations
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RelatedDiagnostic:
    """
    A secondary location relevant to a diagnostic.

    Useful for dependency cycles, duplicated IDs, constraint conflicts, or
    references where both origin and target need to be identified.
    """

    path: DiagnosticPath
    message: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.path, str):
            object.__setattr__(
                self,
                "path",
                DiagnosticPath(self.path),
            )

        message = self.message.strip()

        if "\x00" in message:
            raise ValueError(
                "related diagnostic message must not contain NUL"
            )

        object.__setattr__(self, "message", message)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path.value,
        }

        if self.message:
            payload["message"] = self.message

        return payload


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """
    Canonical machine-readable diagnostic.

    Diagnostics are immutable derived evidence. They may appear in:

    * validation reports;
    * structured warning collections;
    * compilation receipts;
    * diagnostic projections;
    * exception payloads;
    * deterministic proof fixtures.
    """

    code: str
    message: str

    path: DiagnosticPath = field(
        default_factory=DiagnosticPath.root
    )

    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR

    category: DiagnosticCategory = (
        DiagnosticCategory.VALIDATION
    )

    retry: RetryDisposition = RetryDisposition.NEVER

    hint: str | None = None

    context: Mapping[str, object] = field(
        default_factory=dict
    )

    related: tuple[RelatedDiagnostic, ...] = ()

    schema: str = DIAGNOSTIC_SCHEMA

    def __post_init__(self) -> None:
        code = self.code.strip()

        if not code:
            raise ValueError(
                "diagnostic code must not be empty"
            )

        if any(character.isspace() for character in code):
            raise ValueError(
                "diagnostic code must not contain whitespace"
            )

        if "\x00" in code:
            raise ValueError(
                "diagnostic code must not contain NUL"
            )

        message = self.message.strip()

        if not message:
            raise ValueError(
                "diagnostic message must not be empty"
            )

        if "\x00" in message:
            raise ValueError(
                "diagnostic message must not contain NUL"
            )

        path = self.path

        if isinstance(path, str):
            path = DiagnosticPath(path)

        severity = self.severity

        if isinstance(severity, str):
            severity = DiagnosticSeverity[
                severity.strip().upper()
            ]

        category = self.category

        if isinstance(category, str):
            category = DiagnosticCategory(category)

        retry = self.retry

        if isinstance(retry, str):
            retry = RetryDisposition(retry)

        hint = self.hint

        if hint is not None:
            hint = hint.strip()

            if not hint:
                hint = None

            elif "\x00" in hint:
                raise ValueError(
                    "diagnostic hint must not contain NUL"
                )

        related_items: list[RelatedDiagnostic] = []

        for item in self.related:
            if isinstance(item, RelatedDiagnostic):
                related_items.append(item)
                continue

            raise TypeError(
                "diagnostic related locations must be "
                "RelatedDiagnostic instances"
            )

        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "retry", retry)
        object.__setattr__(self, "hint", hint)
        object.__setattr__(
            self,
            "context",
            _freeze_context(self.context),
        )
        object.__setattr__(
            self,
            "related",
            tuple(related_items),
        )

    @property
    def is_error(self) -> bool:
        return self.severity >= DiagnosticSeverity.ERROR

    @property
    def is_warning(self) -> bool:
        return self.severity == DiagnosticSeverity.WARNING

    @property
    def is_fatal(self) -> bool:
        return self.severity >= DiagnosticSeverity.FATAL

    @property
    def retryable(self) -> bool:
        return self.retry == RetryDisposition.RETRYABLE

    @classmethod
    def info(
        cls,
        code: str,
        message: str,
        *,
        path: DiagnosticPath | str = "scene",
        category: DiagnosticCategory = (
            DiagnosticCategory.VALIDATION
        ),
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        related: Sequence[RelatedDiagnostic] = (),
    ) -> Self:
        return cls(
            code=code,
            message=message,
            path=DiagnosticPath(path)
            if isinstance(path, str)
            else path,
            severity=DiagnosticSeverity.INFO,
            category=category,
            hint=hint,
            context=context or {},
            related=tuple(related),
        )

    @classmethod
    def warning(
        cls,
        code: str,
        message: str,
        *,
        path: DiagnosticPath | str = "scene",
        category: DiagnosticCategory = (
            DiagnosticCategory.COMPATIBILITY
        ),
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        related: Sequence[RelatedDiagnostic] = (),
    ) -> Self:
        return cls(
            code=code,
            message=message,
            path=DiagnosticPath(path)
            if isinstance(path, str)
            else path,
            severity=DiagnosticSeverity.WARNING,
            category=category,
            hint=hint,
            context=context or {},
            related=tuple(related),
        )

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        *,
        path: DiagnosticPath | str = "scene",
        category: DiagnosticCategory = (
            DiagnosticCategory.VALIDATION
        ),
        retry: RetryDisposition = RetryDisposition.NEVER,
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        related: Sequence[RelatedDiagnostic] = (),
    ) -> Self:
        return cls(
            code=code,
            message=message,
            path=DiagnosticPath(path)
            if isinstance(path, str)
            else path,
            severity=DiagnosticSeverity.ERROR,
            category=category,
            retry=retry,
            hint=hint,
            context=context or {},
            related=tuple(related),
        )

    @classmethod
    def fatal(
        cls,
        code: str,
        message: str,
        *,
        path: DiagnosticPath | str = "scene",
        category: DiagnosticCategory = (
            DiagnosticCategory.INTERNAL
        ),
        retry: RetryDisposition = RetryDisposition.NEVER,
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        related: Sequence[RelatedDiagnostic] = (),
    ) -> Self:
        return cls(
            code=code,
            message=message,
            path=DiagnosticPath(path)
            if isinstance(path, str)
            else path,
            severity=DiagnosticSeverity.FATAL,
            category=category,
            retry=retry,
            hint=hint,
            context=context or {},
            related=tuple(related),
        )

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "code": self.code,
            "message": self.message,
            "path": self.path.value,
            "severity": self.severity.label,
            "category": self.category.value,
            "retry": self.retry.value,
        }

        if self.hint is not None:
            payload["hint"] = self.hint

        if self.context:
            payload["context"] = {
                key: self.context[key]
                for key in sorted(self.context)
            }

        if self.related:
            payload["related"] = [
                item.as_dict()
                for item in self.related
            ]

        return payload

    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def __str__(self) -> str:
        return (
            f"{self.severity.label.upper()} "
            f"{self.code} @ {self.path}: "
            f"{self.message}"
        )


# ---------------------------------------------------------------------------
# Diagnostic report
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """
    Immutable aggregate of diagnostics from one compiler phase.

    A report may contain warnings without failing compilation. Any ERROR or
    FATAL diagnostic makes ``ok`` false.
    """

    diagnostics: tuple[Diagnostic, ...] = ()

    phase: str = "unspecified"

    schema: str = DIAGNOSTIC_REPORT_SCHEMA

    def __post_init__(self) -> None:
        phase = self.phase.strip()

        if not phase:
            raise ValueError(
                "diagnostic report phase must not be empty"
            )

        normalized: list[Diagnostic] = []

        for diagnostic in self.diagnostics:
            if not isinstance(diagnostic, Diagnostic):
                raise TypeError(
                    "diagnostic report entries must be "
                    "Diagnostic instances"
                )

            normalized.append(diagnostic)

        object.__setattr__(
            self,
            "diagnostics",
            tuple(normalized),
        )
        object.__setattr__(
            self,
            "phase",
            phase,
        )

    def __iter__(self) -> Iterator[Diagnostic]:
        return iter(self.diagnostics)

    def __len__(self) -> int:
        return len(self.diagnostics)

    def __bool__(self) -> bool:
        return bool(self.diagnostics)

    @property
    def ok(self) -> bool:
        return not any(
            diagnostic.is_error
            for diagnostic in self.diagnostics
        )

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.is_error
        )

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.is_warning
        )

    @property
    def infos(self) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity
            == DiagnosticSeverity.INFO
        )

    @property
    def fatal(self) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.is_fatal
        )

    @property
    def highest_severity(
        self,
    ) -> DiagnosticSeverity | None:
        if not self.diagnostics:
            return None

        return max(
            diagnostic.severity
            for diagnostic in self.diagnostics
        )

    def by_code(
        self,
        code: str,
    ) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.code == code
        )

    def by_category(
        self,
        category: DiagnosticCategory,
    ) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.category == category
        )

    def as_dict(self) -> dict[str, object]:
        highest = self.highest_severity

        return {
            "schema": self.schema,
            "phase": self.phase,
            "ok": self.ok,
            "diagnostic_count": len(self.diagnostics),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "info_count": len(self.infos),
            "fatal_count": len(self.fatal),
            "highest_severity": (
                highest.label
                if highest is not None
                else None
            ),
            "diagnostics": [
                diagnostic.as_dict()
                for diagnostic in self.diagnostics
            ],
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


class DiagnosticCollector:
    """
    Mutable ephemeral collector used during a compiler phase.

    Canonical scene objects remain immutable. This collector belongs only
    to ephemeral compilation context and freezes into a DiagnosticReport.
    """

    __slots__ = (
        "_diagnostics",
        "_phase",
    )

    def __init__(
        self,
        *,
        phase: str,
    ) -> None:
        phase = phase.strip()

        if not phase:
            raise ValueError(
                "diagnostic collector phase must not be empty"
            )

        self._phase = phase
        self._diagnostics: list[Diagnostic] = []

    @property
    def phase(self) -> str:
        return self._phase

    def __len__(self) -> int:
        return len(self._diagnostics)

    def __iter__(self) -> Iterator[Diagnostic]:
        return iter(self._diagnostics)

    def add(
        self,
        diagnostic: Diagnostic,
    ) -> Diagnostic:
        if not isinstance(diagnostic, Diagnostic):
            raise TypeError(
                "collector accepts only Diagnostic instances"
            )

        self._diagnostics.append(diagnostic)

        return diagnostic

    def extend(
        self,
        diagnostics: Iterable[Diagnostic],
    ) -> None:
        for diagnostic in diagnostics:
            self.add(diagnostic)

    def info(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> Diagnostic:
        return self.add(
            Diagnostic.info(
                code,
                message,
                **kwargs,
            )
        )

    def warning(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> Diagnostic:
        return self.add(
            Diagnostic.warning(
                code,
                message,
                **kwargs,
            )
        )

    def error(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> Diagnostic:
        return self.add(
            Diagnostic.error(
                code,
                message,
                **kwargs,
            )
        )

    def fatal(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> Diagnostic:
        return self.add(
            Diagnostic.fatal(
                code,
                message,
                **kwargs,
            )
        )

    @property
    def has_errors(self) -> bool:
        return any(
            diagnostic.is_error
            for diagnostic in self._diagnostics
        )

    def freeze(self) -> DiagnosticReport:
        return DiagnosticReport(
            diagnostics=tuple(self._diagnostics),
            phase=self._phase,
        )

    def clear(self) -> None:
        self._diagnostics.clear()


# ---------------------------------------------------------------------------
# Base vector exception
# ---------------------------------------------------------------------------


class VectorError(Exception):
    """
    Base exception for all expected vector compiler failures.

    Subclasses expose stable machine-readable codes and categories.

    Ordinary semantic/compiler errors default to non-retryable. Only
    explicitly transient external failures should opt into RETRYABLE.
    """

    code: ClassVar[str] = "vector.error"

    category: ClassVar[DiagnosticCategory] = (
        DiagnosticCategory.INTERNAL
    )

    severity: ClassVar[DiagnosticSeverity] = (
        DiagnosticSeverity.ERROR
    )

    default_retry: ClassVar[RetryDisposition] = (
        RetryDisposition.NEVER
    )

    def __init__(
        self,
        message: str,
        *,
        path: DiagnosticPath | str = "scene",
        code: str | None = None,
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        related: Sequence[RelatedDiagnostic] = (),
        retry: RetryDisposition | None = None,
    ) -> None:
        message = message.strip()

        if not message:
            message = self.__class__.__name__

        self.path = (
            DiagnosticPath(path)
            if isinstance(path, str)
            else path
        )

        self.error_code = (
            code.strip()
            if code is not None
            else self.code
        )

        self.hint = (
            hint.strip()
            if isinstance(hint, str) and hint.strip()
            else None
        )

        self.context = _freeze_context(context)

        self.related = tuple(related)

        self.retry = (
            retry
            if retry is not None
            else self.default_retry
        )

        self.message = message

        super().__init__(message)

    @property
    def retryable(self) -> bool:
        return self.retry == RetryDisposition.RETRYABLE

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            code=self.error_code,
            message=self.message,
            path=self.path,
            severity=self.severity,
            category=self.category,
            retry=self.retry,
            hint=self.hint,
            context=self.context,
            related=self.related,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": ERROR_SCHEMA,
            "type": self.__class__.__name__,
            "diagnostic": self.to_diagnostic().as_dict(),
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def __str__(self) -> str:
        return (
            f"{self.error_code} @ {self.path}: "
            f"{self.message}"
        )


# ---------------------------------------------------------------------------
# Multi-diagnostic validation exception
# ---------------------------------------------------------------------------


class DiagnosticError(VectorError):
    """
    Base exception for failures containing multiple diagnostics.
    """

    code = "validation.failed"

    category = DiagnosticCategory.VALIDATION

    def __init__(
        self,
        diagnostics: Iterable[Diagnostic],
        *,
        phase: str = "validation",
        message: str | None = None,
    ) -> None:
        report = DiagnosticReport(
            diagnostics=tuple(diagnostics),
            phase=phase,
        )

        if not report.diagnostics:
            raise ValueError(
                "DiagnosticError requires at least one diagnostic"
            )

        self.report = report

        first_error = next(
            (
                diagnostic
                for diagnostic in report.diagnostics
                if diagnostic.is_error
            ),
            report.diagnostics[0],
        )

        if message is None:
            error_count = len(report.errors)
            warning_count = len(report.warnings)

            message = (
                f"{phase} failed with "
                f"{error_count} error(s) and "
                f"{warning_count} warning(s)"
            )

        super().__init__(
            message,
            path=first_error.path,
            context={
                "phase": phase,
                "diagnostic_count": len(report),
                "error_count": len(report.errors),
                "warning_count": len(report.warnings),
            },
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": ERROR_SCHEMA,
            "type": self.__class__.__name__,
            "code": self.code,
            "report": self.report.as_dict(),
        }


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class SceneValidationError(DiagnosticError):
    code = "scene.validation.failed"


class ConstructionValidationError(DiagnosticError):
    code = "construction.validation.failed"

    category = DiagnosticCategory.CONSTRUCTION


class GraphValidationError(DiagnosticError):
    code = "graph.validation.failed"

    category = DiagnosticCategory.DEPENDENCY


class ProjectionValidationError(DiagnosticError):
    code = "projection.validation.failed"


# ---------------------------------------------------------------------------
# Geometry and transform failures
# ---------------------------------------------------------------------------


class GeometryError(VectorError):
    code = "geometry.error"

    category = DiagnosticCategory.GEOMETRY


class InvalidGeometryError(GeometryError):
    code = "geometry.invalid"


class NonFiniteGeometryError(GeometryError):
    code = "geometry.non_finite"


class DegenerateGeometryError(GeometryError):
    code = "geometry.degenerate"


class PathGeometryError(GeometryError):
    code = "geometry.path.invalid"


class PathTopologyError(GeometryError):
    code = "geometry.path.topology"


class ArcGeometryError(GeometryError):
    code = "geometry.arc.invalid"


class BoundsError(GeometryError):
    code = "geometry.bounds.failed"


class TransformError(VectorError):
    code = "transform.error"

    category = DiagnosticCategory.TRANSFORM


class InvalidTransformError(TransformError):
    code = "transform.invalid"


class SingularTransformError(TransformError):
    code = "transform.singular"


# ---------------------------------------------------------------------------
# References and graph failures
# ---------------------------------------------------------------------------


class ReferenceResolutionError(VectorError):
    code = "reference.unresolved"

    category = DiagnosticCategory.REFERENCE


class DuplicateIdentityError(VectorError):
    code = "reference.duplicate_identity"

    category = DiagnosticCategory.REFERENCE


class DuplicateProjectionIdError(VectorError):
    code = "projection.duplicate_id"

    category = DiagnosticCategory.REFERENCE


class DependencyError(VectorError):
    code = "dependency.error"

    category = DiagnosticCategory.DEPENDENCY


class DependencyCycleError(DependencyError):
    code = "dependency.cycle"

    def __init__(
        self,
        message: str = "illegal dependency cycle detected",
        *,
        cycle: Sequence[str] = (),
        path: DiagnosticPath | str = "scene",
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.cycle = tuple(cycle)

        merged_context = dict(context or {})

        if self.cycle:
            merged_context["cycle"] = " -> ".join(
                self.cycle
            )

        related = tuple(
            RelatedDiagnostic(
                path=DiagnosticPath(
                    f"scene/definition[{identity}]"
                ),
                message="participates in dependency cycle",
            )
            for identity in self.cycle
        )

        super().__init__(
            message,
            path=path,
            hint=hint,
            context=merged_context,
            related=related,
        )


class ConstraintError(VectorError):
    code = "constraint.error"

    category = DiagnosticCategory.CONSTRAINT


class ConstraintCycleError(ConstraintError):
    code = "constraint.cycle"

    def __init__(
        self,
        message: str = "illegal constraint cycle detected",
        *,
        cycle: Sequence[str] = (),
        path: DiagnosticPath | str = "scene",
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.cycle = tuple(cycle)

        merged_context = dict(context or {})

        if self.cycle:
            merged_context["cycle"] = " -> ".join(
                self.cycle
            )

        super().__init__(
            message,
            path=path,
            hint=hint,
            context=merged_context,
        )


# ---------------------------------------------------------------------------
# Filter failures
# ---------------------------------------------------------------------------


class FilterError(VectorError):
    code = "filter.error"

    category = DiagnosticCategory.FILTER


class FilterGraphError(FilterError):
    code = "filter.graph.invalid"


class FilterDependencyError(FilterError):
    code = "filter.dependency.invalid"


class FilterPrimitiveError(FilterError):
    code = "filter.primitive.invalid"


# ---------------------------------------------------------------------------
# Resource and security policy failures
# ---------------------------------------------------------------------------


class ResourcePolicyError(VectorError):
    code = "resource.policy"

    category = DiagnosticCategory.RESOURCE


class ExternalResourceError(VectorError):
    code = "resource.external.failed"

    category = DiagnosticCategory.EXTERNAL


class RetryableExternalResourceError(
    ExternalResourceError
):
    code = "resource.external.transient"

    default_retry = RetryDisposition.RETRYABLE


class ExternalResourceUnavailableError(
    ExternalResourceError
):
    code = "resource.external.unavailable"


class ResourceDigestError(ResourcePolicyError):
    code = "resource.digest.failed"


class ResourceSizeError(ResourcePolicyError):
    code = "resource.size.exceeded"


class SecurityPolicyError(VectorError):
    code = "security.policy"

    category = DiagnosticCategory.SECURITY


class URLPolicyError(SecurityPolicyError):
    code = "security.url.rejected"


class ScriptPolicyError(SecurityPolicyError):
    code = "security.script.rejected"


class UnsafeMarkupError(SecurityPolicyError):
    code = "security.raw_markup.rejected"


class EntityPolicyError(SecurityPolicyError):
    code = "security.entity.rejected"


class ExternalEntityError(SecurityPolicyError):
    code = "security.external_entity.rejected"


# ---------------------------------------------------------------------------
# Resource budgets
# ---------------------------------------------------------------------------


class ResourceBudgetError(VectorError):
    code = "resource.budget.exceeded"

    category = DiagnosticCategory.BUDGET

    def __init__(
        self,
        message: str = "vector compilation resource budget exceeded",
        *,
        budget_name: str,
        limit: int | float,
        observed: int | float,
        path: DiagnosticPath | str = "scene",
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
    ) -> None:
        if isinstance(limit, float) and not math.isfinite(limit):
            raise ValueError(
                "budget limit must be finite"
            )

        if isinstance(observed, float) and not math.isfinite(
            observed
        ):
            raise ValueError(
                "budget observation must be finite"
            )

        self.budget_name = budget_name
        self.limit = limit
        self.observed = observed

        merged_context = dict(context or {})
        merged_context.update(
            {
                "budget": budget_name,
                "limit": limit,
                "observed": observed,
            }
        )

        super().__init__(
            message,
            path=path,
            hint=hint,
            context=merged_context,
        )


class SceneNodeBudgetError(ResourceBudgetError):
    code = "resource.budget.scene_nodes"


class DefinitionBudgetError(ResourceBudgetError):
    code = "resource.budget.definitions"


class PathCommandBudgetError(ResourceBudgetError):
    code = "resource.budget.path_commands"


class FilterPrimitiveBudgetError(ResourceBudgetError):
    code = "resource.budget.filter_primitives"


class ProceduralExpansionBudgetError(ResourceBudgetError):
    code = "resource.budget.procedural_expansion"


class EmbeddedByteBudgetError(ResourceBudgetError):
    code = "resource.budget.embedded_bytes"


class OutputByteBudgetError(ResourceBudgetError):
    code = "resource.budget.output_bytes"


class RecursionDepthBudgetError(ResourceBudgetError):
    code = "resource.budget.recursion_depth"


class BackendComplexityBudgetError(ResourceBudgetError):
    code = "resource.budget.backend_complexity"


# ---------------------------------------------------------------------------
# Compatibility and unsupported-feature failures
# ---------------------------------------------------------------------------


class CompatibilityError(VectorError):
    code = "compatibility.error"

    category = DiagnosticCategory.COMPATIBILITY


class UnsupportedProfileError(CompatibilityError):
    code = "compatibility.profile.unsupported"


class UnsupportedFeatureError(CompatibilityError):
    code = "compatibility.feature.unsupported"


class UnknownFeatureError(CompatibilityError):
    code = "compatibility.feature.unknown"


class CompatibilityDegradationError(CompatibilityError):
    code = "compatibility.degradation.disallowed"


# ---------------------------------------------------------------------------
# Serialization failures
# ---------------------------------------------------------------------------


class SerializationError(VectorError):
    code = "serialization.error"

    category = DiagnosticCategory.SERIALIZATION


class NumericSerializationError(SerializationError):
    code = "serialization.number.invalid"


class XMLSerializationError(SerializationError):
    code = "serialization.xml.failed"


class EscapingError(SerializationError):
    code = "serialization.escape.failed"


class NamespaceError(SerializationError):
    code = "serialization.namespace.invalid"


class ReferenceSerializationError(SerializationError):
    code = "serialization.reference.invalid"


# ---------------------------------------------------------------------------
# Backend failures
# ---------------------------------------------------------------------------


class BackendError(VectorError):
    code = "backend.error"

    category = DiagnosticCategory.BACKEND


class BackendUnavailableError(BackendError):
    code = "backend.unavailable"


class BackendIntegrityError(BackendError):
    code = "backend.integrity.failed"


class GeometryBackendError(BackendError):
    code = "backend.geometry.failed"


class ShapingBackendError(BackendError):
    code = "backend.shaping.failed"


class RasterBackendError(BackendError):
    code = "backend.raster.failed"


# ---------------------------------------------------------------------------
# Schema/version failures
# ---------------------------------------------------------------------------


class SchemaError(VectorError):
    code = "schema.error"

    category = DiagnosticCategory.SCHEMA


class SchemaVersionError(SchemaError):
    code = "schema.version.unsupported"


class SceneSchemaError(SchemaError):
    code = "schema.scene.invalid"


class SchemaMigrationError(SchemaError):
    code = "schema.migration.failed"


# ---------------------------------------------------------------------------
# Cache failures
# ---------------------------------------------------------------------------


class CacheError(VectorError):
    code = "cache.error"

    category = DiagnosticCategory.CACHE


class CacheIntegrityError(CacheError):
    code = "cache.integrity.failed"


class CacheVersionError(CacheError):
    code = "cache.version.invalid"


# ---------------------------------------------------------------------------
# Persistence and destination failures
# ---------------------------------------------------------------------------


class PersistenceError(VectorError):
    code = "persistence.error"

    category = DiagnosticCategory.PERSISTENCE


class DestinationPolicyError(PersistenceError):
    code = "persistence.destination.rejected"


class PathTraversalError(DestinationPolicyError):
    code = "persistence.path_traversal.rejected"


class AtomicWriteError(PersistenceError):
    code = "persistence.atomic_write.failed"


class FsyncError(PersistenceError):
    code = "persistence.fsync.failed"


class OutputIntegrityError(PersistenceError):
    code = "persistence.output_integrity.failed"


# ---------------------------------------------------------------------------
# Internal invariant failures
# ---------------------------------------------------------------------------


class InternalVectorError(VectorError):
    """
    Compiler invariant failure.

    This class is for impossible internal states, not malformed user scenes.
    """

    code = "vector.internal"

    category = DiagnosticCategory.INTERNAL

    severity = DiagnosticSeverity.FATAL


class InvariantViolationError(InternalVectorError):
    code = "vector.internal.invariant"


# ---------------------------------------------------------------------------
# Structured warnings
# ---------------------------------------------------------------------------


def compatibility_downgrade_warning(
    *,
    feature: str,
    profile: str,
    path: DiagnosticPath | str = "scene",
    message: str | None = None,
) -> Diagnostic:
    return Diagnostic.warning(
        code="warning.compatibility_downgrade",
        message=message or (
            f"feature {feature!r} was downgraded for "
            f"compatibility profile {profile!r}"
        ),
        path=path,
        category=DiagnosticCategory.COMPATIBILITY,
        context={
            "feature": feature,
            "profile": profile,
        },
    )


def unsupported_optional_feature_warning(
    *,
    feature: str,
    path: DiagnosticPath | str = "scene",
) -> Diagnostic:
    return Diagnostic.warning(
        code="warning.optional_feature_unsupported",
        message=(
            f"optional feature {feature!r} is unsupported "
            "and was omitted under the active policy"
        ),
        path=path,
        category=DiagnosticCategory.COMPATIBILITY,
        context={
            "feature": feature,
        },
    )


def external_resource_omitted_warning(
    *,
    resource: str,
    path: DiagnosticPath | str = "scene",
) -> Diagnostic:
    return Diagnostic.warning(
        code="warning.external_resource_omitted",
        message=(
            f"external resource {resource!r} was omitted "
            "under the active resource policy"
        ),
        path=path,
        category=DiagnosticCategory.RESOURCE,
        context={
            "resource": resource,
        },
    )


def approximation_applied_warning(
    *,
    operation: str,
    path: DiagnosticPath | str = "scene",
    tolerance: float | None = None,
) -> Diagnostic:
    context: dict[str, object] = {
        "operation": operation,
    }

    if tolerance is not None:
        context["tolerance"] = tolerance

    return Diagnostic.warning(
        code="warning.approximation_applied",
        message=(
            f"deterministic approximation applied during "
            f"{operation!r}"
        ),
        path=path,
        category=DiagnosticCategory.GEOMETRY,
        context=context,
    )


def font_fallback_warning(
    *,
    requested_font: str,
    fallback_font: str,
    path: DiagnosticPath | str = "scene",
) -> Diagnostic:
    return Diagnostic.warning(
        code="warning.font_fallback",
        message=(
            f"font {requested_font!r} was unavailable; "
            f"fallback {fallback_font!r} was selected"
        ),
        path=path,
        category=DiagnosticCategory.COMPATIBILITY,
        context={
            "requested_font": requested_font,
            "fallback_font": fallback_font,
        },
    )


def filter_region_expanded_warning(
    *,
    path: DiagnosticPath | str = "scene",
    reason: str = "conservative effect bounds",
) -> Diagnostic:
    return Diagnostic.warning(
        code="warning.filter_region_expanded",
        message=(
            "filter region was conservatively expanded "
            "to avoid effect clipping"
        ),
        path=path,
        category=DiagnosticCategory.FILTER,
        context={
            "reason": reason,
        },
    )


# ---------------------------------------------------------------------------
# Error/report helpers
# ---------------------------------------------------------------------------


def report_from(
    diagnostics: Iterable[Diagnostic],
    *,
    phase: str,
) -> DiagnosticReport:
    """
    Freeze an iterable of diagnostics into a report.
    """

    return DiagnosticReport(
        diagnostics=tuple(diagnostics),
        phase=phase,
    )


def raise_for_report(
    report: DiagnosticReport,
    *,
    error_type: type[DiagnosticError] = (
        SceneValidationError
    ),
) -> None:
    """
    Raise ``error_type`` when a report contains correctness failures.

    Warnings alone never trigger this helper.
    """

    if not issubclass(error_type, DiagnosticError):
        raise TypeError(
            "error_type must derive from DiagnosticError"
        )

    if report.ok:
        return

    raise error_type(
        report.diagnostics,
        phase=report.phase,
    )


def ensure_finite(
    value: float,
    *,
    path: DiagnosticPath | str = "scene",
    name: str = "value",
) -> float:
    """
    Validate a finite real number with a typed geometry failure.

    This is intentionally available from the errors module because finite
    real-number validation is used throughout scene construction, transforms,
    geometry, numeric serialization, filters, and resource policies.
    """

    if isinstance(value, bool):
        raise NonFiniteGeometryError(
            f"{name} must be a finite real number, not boolean",
            path=path,
            context={
                "name": name,
            },
        )

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise NonFiniteGeometryError(
            f"{name} must be a finite real number",
            path=path,
            context={
                "name": name,
            },
        ) from exc

    if not math.isfinite(numeric):
        raise NonFiniteGeometryError(
            f"{name} must be finite",
            path=path,
            context={
                "name": name,
            },
        )

    return numeric


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


__all__ = [
    # Schema/module identity
    "DIAGNOSTIC_SCHEMA",
    "DIAGNOSTIC_REPORT_SCHEMA",
    "ERROR_SCHEMA",
    "MODULE_VERSION",

    # Diagnostic primitives
    "DiagnosticSeverity",
    "DiagnosticCategory",
    "RetryDisposition",
    "DiagnosticPathError",
    "DiagnosticPath",
    "RelatedDiagnostic",
    "Diagnostic",
    "DiagnosticReport",
    "DiagnosticCollector",

    # Base exception model
    "VectorError",
    "DiagnosticError",

    # Validation
    "SceneValidationError",
    "ConstructionValidationError",
    "GraphValidationError",
    "ProjectionValidationError",

    # Geometry
    "GeometryError",
    "InvalidGeometryError",
    "NonFiniteGeometryError",
    "DegenerateGeometryError",
    "PathGeometryError",
    "PathTopologyError",
    "ArcGeometryError",
    "BoundsError",

    # Transform
    "TransformError",
    "InvalidTransformError",
    "SingularTransformError",

    # References/dependencies
    "ReferenceResolutionError",
    "DuplicateIdentityError",
    "DuplicateProjectionIdError",
    "DependencyError",
    "DependencyCycleError",
    "ConstraintError",
    "ConstraintCycleError",

    # Filters
    "FilterError",
    "FilterGraphError",
    "FilterDependencyError",
    "FilterPrimitiveError",

    # Resources/security
    "ResourcePolicyError",
    "ExternalResourceError",
    "RetryableExternalResourceError",
    "ExternalResourceUnavailableError",
    "ResourceDigestError",
    "ResourceSizeError",
    "SecurityPolicyError",
    "URLPolicyError",
    "ScriptPolicyError",
    "UnsafeMarkupError",
    "EntityPolicyError",
    "ExternalEntityError",

    # Budgets
    "ResourceBudgetError",
    "SceneNodeBudgetError",
    "DefinitionBudgetError",
    "PathCommandBudgetError",
    "FilterPrimitiveBudgetError",
    "ProceduralExpansionBudgetError",
    "EmbeddedByteBudgetError",
    "OutputByteBudgetError",
    "RecursionDepthBudgetError",
    "BackendComplexityBudgetError",

    # Compatibility
    "CompatibilityError",
    "UnsupportedProfileError",
    "UnsupportedFeatureError",
    "UnknownFeatureError",
    "CompatibilityDegradationError",

    # Serialization
    "SerializationError",
    "NumericSerializationError",
    "XMLSerializationError",
    "EscapingError",
    "NamespaceError",
    "ReferenceSerializationError",

    # Backends
    "BackendError",
    "BackendUnavailableError",
    "BackendIntegrityError",
    "GeometryBackendError",
    "ShapingBackendError",
    "RasterBackendError",

    # Schema
    "SchemaError",
    "SchemaVersionError",
    "SceneSchemaError",
    "SchemaMigrationError",

    # Cache
    "CacheError",
    "CacheIntegrityError",
    "CacheVersionError",

    # Persistence
    "PersistenceError",
    "DestinationPolicyError",
    "PathTraversalError",
    "AtomicWriteError",
    "FsyncError",
    "OutputIntegrityError",

    # Internal invariants
    "InternalVectorError",
    "InvariantViolationError",

    # Structured warning constructors
    "compatibility_downgrade_warning",
    "unsupported_optional_feature_warning",
    "external_resource_omitted_warning",
    "approximation_applied_warning",
    "font_fallback_warning",
    "filter_region_expanded_warning",

    # Helpers
    "report_from",
    "raise_for_report",
    "ensure_finite",
]
