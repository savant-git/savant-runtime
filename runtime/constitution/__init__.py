"""Recursive constitutional infrastructure above Savant's executable runtime."""

from .graph import ConstitutionalGraph
from .bootstrap import ConstitutionalBootstrap, bootstrap
from .kinds import KindRegistry
from .object import ConstitutionalObject
from .projection import ProjectionArtifact, ProjectionCache, ProjectionContext, ProjectionEngine
from .resolver import ConstitutionalResolver
from .reflection import RuntimeReflection
from .engines import DependencyEngine, LineageEngine, ProvenanceEngine
from .recursive import InheritanceEngine, RECURSIVE_KINDS, RecursiveConstitution
from .paths import ConstitutionalPathResolver
from .temporal import TemporalConstitution
from .pipeline import ConstitutionalProjectionPipeline, PIPELINE_STAGES, PipelineState
from .diff import ConstitutionalDiff, ConstitutionalDiffer
from .audit import ConstitutionalSelfAudit
from .contributions import AssertionContribution, ConstitutionalAssertionAPI
from .authority import AuthorityResolver, AuthorityValidationError
from .events import ConstitutionalEvent, ConstitutionalEventLog
from .extensions import ConstitutionalExtensions
from .identity import CanonicalIdentityResolver, IdentityCollisionError, IdentityMigration
from .versioning import ConstitutionalVersions, SemanticVersion
from .migration import RuntimeDescriptor, RuntimeMigration, RuntimeMigrationPluginRegistry, convergence_report, convergence_report_markdown, discover_runtime, migration_report
from .relationships import RelationshipTypeRegistry
from .readiness import migration_readiness_report
from .validation import ConstitutionalValidator, RuntimeMigrationValidator
from .registry import ConstitutionalRegistry, ConstitutionalValidationError
from .schema import ConstitutionalSchemaRegistry, SchemaValidationError
from .platform import (BusEvent, ConstitutionalBus, ConstitutionalCapability, ConstitutionalPlatform,
    ConstitutionalPlugin, ConstitutionalSubsystemContract, Diagnostic, FUTURE_ATTACHMENT_POINTS,
    FutureSubsystemInterface, HealthProjection, HealthState, LifecyclePhase, LifecycleTracker,
    LifecycleTransitionError, Metric, SubsystemAttachment, subsystem_entrypoint)

__all__ = [
    "ConstitutionalBootstrap", "ConstitutionalGraph", "ConstitutionalObject", "ConstitutionalRegistry",
    "ConstitutionalSchemaRegistry", "ConstitutionalValidationError", "KindRegistry",
    "ProjectionArtifact", "ProjectionCache", "ProjectionContext", "ProjectionEngine", "RelationshipTypeRegistry", "SchemaValidationError",
    "ConstitutionalResolver", "RuntimeReflection", "DependencyEngine", "LineageEngine", "ProvenanceEngine",
    "InheritanceEngine", "RECURSIVE_KINDS", "RecursiveConstitution", "ConstitutionalPathResolver", "TemporalConstitution",
    "ConstitutionalProjectionPipeline", "PIPELINE_STAGES", "PipelineState", "ConstitutionalDiff", "ConstitutionalDiffer",
    "ConstitutionalSelfAudit", "AssertionContribution", "ConstitutionalAssertionAPI",
    "AuthorityResolver", "AuthorityValidationError", "CanonicalIdentityResolver", "IdentityCollisionError", "IdentityMigration",
    "ConstitutionalEvent", "ConstitutionalEventLog", "ConstitutionalExtensions", "ConstitutionalVersions", "SemanticVersion",
    "RuntimeDescriptor", "RuntimeMigration", "RuntimeMigrationPluginRegistry", "RuntimeMigrationValidator", "convergence_report", "convergence_report_markdown", "discover_runtime", "migration_report",
    "ConstitutionalValidator", "bootstrap", "migration_readiness_report",
    "BusEvent", "ConstitutionalBus", "ConstitutionalCapability", "ConstitutionalPlatform", "ConstitutionalPlugin",
    "ConstitutionalSubsystemContract", "Diagnostic", "FUTURE_ATTACHMENT_POINTS", "FutureSubsystemInterface",
    "HealthProjection", "HealthState", "LifecyclePhase", "LifecycleTracker", "LifecycleTransitionError",
    "Metric", "SubsystemAttachment", "subsystem_entrypoint",
]
