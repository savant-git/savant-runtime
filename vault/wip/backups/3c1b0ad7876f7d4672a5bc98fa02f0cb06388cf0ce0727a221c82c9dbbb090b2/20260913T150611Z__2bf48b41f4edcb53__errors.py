from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    path: str
    severity: str = "error"


class VectorError(ValueError):
    """Base class for deterministic vector-kernel failures."""

    code = "vector.error"

    def __init__(self, message: str, *, path: str = "scene") -> None:
        self.path = path
        super().__init__(message)


class SceneValidationError(VectorError):
    code = "scene.validation"

    def __init__(self, diagnostics: Iterable[Diagnostic]):
        self.diagnostics = tuple(diagnostics)
        message = "; ".join(
            f"{item.code}@{item.path}: {item.message}"
            for item in self.diagnostics
        )
        super().__init__(message or "scene validation failed")


class ResourceBudgetError(VectorError):
    code = "resource.budget"


class ProjectionValidationError(VectorError):
    code = "projection.validation"

    def __init__(self, diagnostics: Iterable[Diagnostic]):
        self.diagnostics = tuple(diagnostics)
        message = "; ".join(
            f"{item.code}@{item.path}: {item.message}"
            for item in self.diagnostics
        )
        super().__init__(message or "projection validation failed")


class DestinationPolicyError(VectorError):
    code = "destination.policy"


class UnsupportedProfileError(VectorError):
    code = "profile.unsupported"
