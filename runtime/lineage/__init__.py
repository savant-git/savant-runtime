"""System-wide functional lineage primitives."""

from .engine import (
    LineageGraph,
    compile_lineage,
)

from .model import (
    LineageBinding,
    LineageError,
    LineageValidationError,
)

from .projection import (
    family_projection,
    legacy_hierarchy_projection,
)

from .references import (
    ReferenceResolution,
    filesystem_reference_id,
    normalize_reference,
    resolve_reference,
)

from .registry import (
    LineageRoleRegistry,
    RoleDefinition,
)

__all__ = [
    "LineageBinding",
    "LineageError",
    "LineageGraph",
    "LineageRoleRegistry",
    "LineageValidationError",
    "ReferenceResolution",
    "RoleDefinition",
    "compile_lineage",
    "family_projection",
    "filesystem_reference_id",
    "legacy_hierarchy_projection",
    "normalize_reference",
    "resolve_reference",
]
