"""
SAVANT Filament Vector Renderer
errors.py self-test suite.

This module exercises the public contract of the vector renderer's
diagnostic and exception subsystem.

The suite intentionally avoids third-party dependencies and uses Python's
standard unittest framework so it can run anywhere the Filament vector
runtime runs.

Run directly with:

    python3 test_errors.py

Or through unittest discovery with:

    python3 -m unittest -v test_errors.py
"""

from __future__ import annotations

import json
import math
import unittest

from errors import (
    DIAGNOSTIC_REPORT_SCHEMA,
    DIAGNOSTIC_SCHEMA,
    ERROR_SCHEMA,
    MODULE_VERSION,
    ArcGeometryError,
    AtomicWriteError,
    BackendComplexityBudgetError,
    BackendIntegrityError,
    CacheIntegrityError,
    CompatibilityDegradationError,
    CompatibilityError,
    ConstraintCycleError,
    ConstructionValidationError,
    DefinitionBudgetError,
    DependencyCycleError,
    Diagnostic,
    DiagnosticCategory,
    DiagnosticCollector,
    DiagnosticError,
    DiagnosticPath,
    DiagnosticPathError,
    DiagnosticReport,
    DiagnosticSeverity,
    DestinationPolicyError,
    DuplicateIdentityError,
    DuplicateProjectionIdError,
    EmbeddedByteBudgetError,
    EntityPolicyError,
    EscapingError,
    ExternalEntityError,
    ExternalResourceUnavailableError,
    FilterDependencyError,
    FilterGraphError,
    FilterPrimitiveBudgetError,
    FilterPrimitiveError,
    FsyncError,
    GeometryBackendError,
    GeometryError,
    GraphValidationError,
    InternalVectorError,
    InvalidGeometryError,
    InvalidTransformError,
    InvariantViolationError,
    NamespaceError,
    NonFiniteGeometryError,
    NumericSerializationError,
    OutputByteBudgetError,
    OutputIntegrityError,
    PathCommandBudgetError,
    PathGeometryError,
    PathTopologyError,
    PathTraversalError,
    PersistenceError,
    ProceduralExpansionBudgetError,
    ProjectionValidationError,
    RasterBackendError,
    RecursionDepthBudgetError,
    ReferenceResolutionError,
    ReferenceSerializationError,
    RelatedDiagnostic,
    ResourceBudgetError,
    ResourceDigestError,
    ResourcePolicyError,
    ResourceSizeError,
    RetryDisposition,
    RetryableExternalResourceError,
    SceneNodeBudgetError,
    SceneSchemaError,
    SceneValidationError,
    SchemaMigrationError,
    SchemaVersionError,
    ScriptPolicyError,
    SecurityPolicyError,
    SerializationError,
    ShapingBackendError,
    SingularTransformError,
    TransformError,
    URLPolicyError,
    UnknownFeatureError,
    UnsafeMarkupError,
    UnsupportedFeatureError,
    UnsupportedProfileError,
    VectorError,
    XMLSerializationError,
    approximation_applied_warning,
    compatibility_downgrade_warning,
    ensure_finite,
    external_resource_omitted_warning,
    filter_region_expanded_warning,
    font_fallback_warning,
    raise_for_report,
    report_from,
    unsupported_optional_feature_warning,
)


class SchemaIdentityTests(unittest.TestCase):
    def test_schema_constants_exist(self) -> None:
        self.assertEqual(
            DIAGNOSTIC_SCHEMA,
            "savant://filament/vector/diagnostic/1.0.0",
        )

        self.assertEqual(
            DIAGNOSTIC_REPORT_SCHEMA,
            "savant://filament/vector/diagnostic-report/1.0.0",
        )

        self.assertEqual(
            ERROR_SCHEMA,
            "savant://filament/vector/error/1.0.0",
        )

        self.assertEqual(
            MODULE_VERSION,
            "1.0.0",
        )


class DiagnosticPathTests(unittest.TestCase):
    def test_root_path(self) -> None:
        path = DiagnosticPath.root()

        self.assertEqual(
            str(path),
            "scene",
        )

    def test_path_normalization(self) -> None:
        path = DiagnosticPath(
            "scene//root///group[logo]"
        )

        self.assertEqual(
            str(path),
            "scene/root/group[logo]",
        )

    def test_semantic_path_construction(self) -> None:
        path = (
            DiagnosticPath.root()
            .child("root")
            .child("group", "logo")
            .child("mask", "cutout")
            .indexed("path", 3)
        )

        self.assertEqual(
            str(path),
            (
                "scene/root/group[logo]/"
                "mask[cutout]/path[3]"
            ),
        )

    def test_negative_index_rejected(self) -> None:
        with self.assertRaises(
            DiagnosticPathError
        ):
            DiagnosticPath.root().indexed(
                "path",
                -1,
            )

    def test_empty_path_rejected(self) -> None:
        with self.assertRaises(
            DiagnosticPathError
        ):
            DiagnosticPath("")

    def test_nul_path_rejected(self) -> None:
        with self.assertRaises(
            DiagnosticPathError
        ):
            DiagnosticPath(
                "scene/\x00bad"
            )

    def test_child_with_slash_rejected(self) -> None:
        with self.assertRaises(
            DiagnosticPathError
        ):
            DiagnosticPath.root().child(
                "bad/segment"
            )


class DiagnosticTests(unittest.TestCase):
    def test_error_diagnostic(self) -> None:
        diagnostic = Diagnostic.error(
            "proof.error",
            "proof error operational",
            path="scene/root",
        )

        self.assertEqual(
            diagnostic.code,
            "proof.error",
        )

        self.assertEqual(
            diagnostic.message,
            "proof error operational",
        )

        self.assertEqual(
            diagnostic.path,
            DiagnosticPath(
                "scene/root"
            ),
        )

        self.assertEqual(
            diagnostic.severity,
            DiagnosticSeverity.ERROR,
        )

        self.assertEqual(
            diagnostic.category,
            DiagnosticCategory.VALIDATION,
        )

        self.assertTrue(
            diagnostic.is_error
        )

        self.assertFalse(
            diagnostic.is_warning
        )

        self.assertFalse(
            diagnostic.retryable
        )

    def test_warning_diagnostic(self) -> None:
        diagnostic = Diagnostic.warning(
            "proof.warning",
            "proof warning operational",
            path="scene/root",
        )

        self.assertEqual(
            diagnostic.severity,
            DiagnosticSeverity.WARNING,
        )

        self.assertTrue(
            diagnostic.is_warning
        )

        self.assertFalse(
            diagnostic.is_error
        )

    def test_info_diagnostic(self) -> None:
        diagnostic = Diagnostic.info(
            "proof.info",
            "proof information operational",
        )

        self.assertEqual(
            diagnostic.severity,
            DiagnosticSeverity.INFO,
        )

    def test_fatal_diagnostic(self) -> None:
        diagnostic = Diagnostic.fatal(
            "proof.fatal",
            "proof fatal diagnostic operational",
        )

        self.assertTrue(
            diagnostic.is_fatal
        )

        self.assertTrue(
            diagnostic.is_error
        )

    def test_diagnostic_context_is_frozen(self) -> None:
        source = {
            "alpha": 1,
            "beta": "two",
        }

        diagnostic = Diagnostic.error(
            "proof.context",
            "context test",
            context=source,
        )

        source["alpha"] = 999

        self.assertEqual(
            diagnostic.context["alpha"],
            1,
        )

        with self.assertRaises(
            TypeError
        ):
            diagnostic.context["gamma"] = 3

    def test_non_finite_context_rejected(self) -> None:
        with self.assertRaises(
            ValueError
        ):
            Diagnostic.error(
                "proof.context.nan",
                "invalid context",
                context={
                    "value": math.nan,
                },
            )

    def test_related_diagnostics(self) -> None:
        related = RelatedDiagnostic(
            path=DiagnosticPath(
                "scene/definition[source]"
            ),
            message="source location",
        )

        diagnostic = Diagnostic.error(
            "proof.related",
            "related diagnostic test",
            path="scene/definition[target]",
            related=(related,),
        )

        self.assertEqual(
            len(diagnostic.related),
            1,
        )

        payload = diagnostic.as_dict()

        self.assertEqual(
            payload["related"][0]["path"],
            "scene/definition[source]",
        )

    def test_canonical_json_is_deterministic(self) -> None:
        first = Diagnostic.error(
            "proof.json",
            "canonical JSON test",
            context={
                "zeta": 2,
                "alpha": 1,
            },
        )

        second = Diagnostic.error(
            "proof.json",
            "canonical JSON test",
            context={
                "alpha": 1,
                "zeta": 2,
            },
        )

        self.assertEqual(
            first.canonical_json(),
            second.canonical_json(),
        )

        parsed = json.loads(
            first.canonical_json()
        )

        self.assertEqual(
            parsed["code"],
            "proof.json",
        )

    def test_empty_code_rejected(self) -> None:
        with self.assertRaises(
            ValueError
        ):
            Diagnostic.error(
                "",
                "message",
            )

    def test_whitespace_in_code_rejected(self) -> None:
        with self.assertRaises(
            ValueError
        ):
            Diagnostic.error(
                "bad code",
                "message",
            )

    def test_empty_message_rejected(self) -> None:
        with self.assertRaises(
            ValueError
        ):
            Diagnostic.error(
                "proof.empty",
                "",
            )


class DiagnosticReportTests(unittest.TestCase):
    def make_report(
        self,
    ) -> DiagnosticReport:
        return DiagnosticReport(
            phase="proof-validation",
            diagnostics=(
                Diagnostic.info(
                    "proof.info",
                    "information",
                ),
                Diagnostic.warning(
                    "proof.warning",
                    "warning",
                ),
                Diagnostic.error(
                    "proof.error",
                    "error",
                ),
            ),
        )

    def test_report_counts(self) -> None:
        report = self.make_report()

        self.assertEqual(
            len(report),
            3,
        )

        self.assertEqual(
            len(report.infos),
            1,
        )

        self.assertEqual(
            len(report.warnings),
            1,
        )

        self.assertEqual(
            len(report.errors),
            1,
        )

        self.assertFalse(
            report.ok
        )

    def test_highest_severity(self) -> None:
        report = self.make_report()

        self.assertEqual(
            report.highest_severity,
            DiagnosticSeverity.ERROR,
        )

    def test_report_by_code(self) -> None:
        report = self.make_report()

        matches = report.by_code(
            "proof.error"
        )

        self.assertEqual(
            len(matches),
            1,
        )

    def test_report_by_category(self) -> None:
        report = DiagnosticReport(
            phase="category-proof",
            diagnostics=(
                Diagnostic.warning(
                    "proof.compatibility",
                    "compatibility warning",
                    category=(
                        DiagnosticCategory.COMPATIBILITY
                    ),
                ),
            ),
        )

        matches = report.by_category(
            DiagnosticCategory.COMPATIBILITY
        )

        self.assertEqual(
            len(matches),
            1,
        )

    def test_empty_report_is_ok(self) -> None:
        report = DiagnosticReport(
            phase="empty-proof"
        )

        self.assertTrue(
            report.ok
        )

        self.assertIsNone(
            report.highest_severity
        )

    def test_report_json(self) -> None:
        report = self.make_report()

        payload = json.loads(
            report.canonical_json()
        )

        self.assertEqual(
            payload["phase"],
            "proof-validation",
        )

        self.assertEqual(
            payload["diagnostic_count"],
            3,
        )


class DiagnosticCollectorTests(unittest.TestCase):
    def test_collector_lifecycle(self) -> None:
        collector = DiagnosticCollector(
            phase="collector-proof"
        )

        self.assertEqual(
            len(collector),
            0,
        )

        collector.info(
            "proof.info",
            "info",
        )

        collector.warning(
            "proof.warning",
            "warning",
        )

        collector.error(
            "proof.error",
            "error",
        )

        self.assertEqual(
            len(collector),
            3,
        )

        self.assertTrue(
            collector.has_errors
        )

        report = collector.freeze()

        self.assertEqual(
            report.phase,
            "collector-proof",
        )

        self.assertFalse(
            report.ok
        )

        collector.clear()

        self.assertEqual(
            len(collector),
            0,
        )

    def test_collector_rejects_non_diagnostic(
        self,
    ) -> None:
        collector = DiagnosticCollector(
            phase="collector-proof"
        )

        with self.assertRaises(
            TypeError
        ):
            collector.add(
                "not-a-diagnostic"
            )


class VectorErrorTests(unittest.TestCase):
    def test_base_vector_error(self) -> None:
        error = VectorError(
            "base vector failure",
            path="scene/root",
        )

        self.assertEqual(
            error.error_code,
            "vector.error",
        )

        self.assertEqual(
            str(error.path),
            "scene/root",
        )

        self.assertFalse(
            error.retryable
        )

    def test_error_to_diagnostic(self) -> None:
        error = InvalidGeometryError(
            "geometry invalid",
            path="scene/path[1]",
        )

        diagnostic = error.to_diagnostic()

        self.assertEqual(
            diagnostic.code,
            "geometry.invalid",
        )

        self.assertEqual(
            diagnostic.category,
            DiagnosticCategory.GEOMETRY,
        )

    def test_error_json(self) -> None:
        error = URLPolicyError(
            "URL rejected",
            path="scene/image[hero]",
        )

        payload = json.loads(
            error.canonical_json()
        )

        self.assertEqual(
            payload["schema"],
            ERROR_SCHEMA,
        )

        self.assertEqual(
            payload["type"],
            "URLPolicyError",
        )

    def test_retryable_external_failure(
        self,
    ) -> None:
        error = RetryableExternalResourceError(
            "temporary network failure",
            path="scene/resource[texture]",
        )

        self.assertTrue(
            error.retryable
        )

        self.assertEqual(
            error.retry,
            RetryDisposition.RETRYABLE,
        )

    def test_non_retryable_semantic_failure(
        self,
    ) -> None:
        error = PathGeometryError(
            "invalid path geometry",
        )

        self.assertFalse(
            error.retryable
        )


class DiagnosticErrorTests(unittest.TestCase):
    def test_scene_validation_error(
        self,
    ) -> None:
        diagnostics = (
            Diagnostic.error(
                "scene.bad",
                "scene is invalid",
                path="scene/root",
            ),
            Diagnostic.warning(
                "scene.warning",
                "scene warning",
            ),
        )

        error = SceneValidationError(
            diagnostics,
            phase="scene-proof",
        )

        self.assertEqual(
            len(error.report),
            2,
        )

        self.assertFalse(
            error.report.ok
        )

    def test_empty_diagnostic_error_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            DiagnosticError(
                (),
                phase="empty",
            )

    def test_raise_for_report(self) -> None:
        report = DiagnosticReport(
            phase="raise-proof",
            diagnostics=(
                Diagnostic.error(
                    "proof.error",
                    "proof failure",
                ),
            ),
        )

        with self.assertRaises(
            SceneValidationError
        ):
            raise_for_report(
                report,
                error_type=(
                    SceneValidationError
                ),
            )

    def test_raise_for_report_ignores_warnings(
        self,
    ) -> None:
        report = DiagnosticReport(
            phase="warning-only",
            diagnostics=(
                Diagnostic.warning(
                    "proof.warning",
                    "warning only",
                ),
            ),
        )

        raise_for_report(
            report,
            error_type=SceneValidationError,
        )


class DependencyCycleTests(unittest.TestCase):
    def test_dependency_cycle(self) -> None:
        cycle = DependencyCycleError(
            cycle=(
                "mask-a",
                "filter-b",
                "mask-a",
            ),
            path="scene/definitions",
        )

        self.assertEqual(
            cycle.cycle,
            (
                "mask-a",
                "filter-b",
                "mask-a",
            ),
        )

        self.assertIn(
            "mask-a -> filter-b -> mask-a",
            cycle.context["cycle"],
        )

        self.assertEqual(
            len(cycle.related),
            3,
        )

    def test_constraint_cycle(self) -> None:
        cycle = ConstraintCycleError(
            cycle=(
                "a",
                "b",
                "c",
                "a",
            ),
        )

        self.assertEqual(
            cycle.cycle[0],
            "a",
        )

        self.assertEqual(
            cycle.cycle[-1],
            "a",
        )


class ResourceBudgetTests(unittest.TestCase):
    def test_generic_budget(self) -> None:
        error = ResourceBudgetError(
            budget_name="scene_nodes",
            limit=1000,
            observed=1001,
            path="scene/root",
        )

        self.assertEqual(
            error.limit,
            1000,
        )

        self.assertEqual(
            error.observed,
            1001,
        )

        self.assertEqual(
            error.context["budget"],
            "scene_nodes",
        )

    def test_specialized_budget_classes(
        self,
    ) -> None:
        classes = (
            SceneNodeBudgetError,
            DefinitionBudgetError,
            PathCommandBudgetError,
            FilterPrimitiveBudgetError,
            ProceduralExpansionBudgetError,
            EmbeddedByteBudgetError,
            OutputByteBudgetError,
            RecursionDepthBudgetError,
            BackendComplexityBudgetError,
        )

        for error_type in classes:
            with self.subTest(
                error_type=error_type.__name__
            ):
                error = error_type(
                    budget_name="proof",
                    limit=10,
                    observed=11,
                )

                self.assertIsInstance(
                    error,
                    ResourceBudgetError,
                )

    def test_non_finite_budget_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            ResourceBudgetError(
                budget_name="proof",
                limit=math.inf,
                observed=1,
            )


class WarningFactoryTests(unittest.TestCase):
    def test_compatibility_warning(
        self,
    ) -> None:
        warning = (
            compatibility_downgrade_warning(
                feature="mesh-gradient",
                profile="portable-static",
                path="scene/paint[hero]",
            )
        )

        self.assertTrue(
            warning.is_warning
        )

        self.assertEqual(
            warning.category,
            DiagnosticCategory.COMPATIBILITY,
        )

    def test_optional_feature_warning(
        self,
    ) -> None:
        warning = (
            unsupported_optional_feature_warning(
                feature="experimental-proof"
            )
        )

        self.assertTrue(
            warning.is_warning
        )

    def test_external_resource_warning(
        self,
    ) -> None:
        warning = (
            external_resource_omitted_warning(
                resource="https://example.invalid/a.png"
            )
        )

        self.assertEqual(
            warning.category,
            DiagnosticCategory.RESOURCE,
        )

    def test_approximation_warning(
        self,
    ) -> None:
        warning = (
            approximation_applied_warning(
                operation="flatten-path",
                tolerance=0.01,
            )
        )

        self.assertEqual(
            warning.context["operation"],
            "flatten-path",
        )

        self.assertEqual(
            warning.context["tolerance"],
            0.01,
        )

    def test_font_fallback_warning(
        self,
    ) -> None:
        warning = font_fallback_warning(
            requested_font="Impossible Sans",
            fallback_font="DejaVu Sans",
        )

        self.assertEqual(
            warning.context["requested_font"],
            "Impossible Sans",
        )

    def test_filter_region_warning(
        self,
    ) -> None:
        warning = (
            filter_region_expanded_warning()
        )

        self.assertEqual(
            warning.category,
            DiagnosticCategory.FILTER,
        )


class EnsureFiniteTests(unittest.TestCase):
    def test_integer(self) -> None:
        result = ensure_finite(
            42,
            name="x",
        )

        self.assertEqual(
            result,
            42.0,
        )

    def test_float(self) -> None:
        result = ensure_finite(
            42.5,
            name="x",
        )

        self.assertEqual(
            result,
            42.5,
        )

    def test_string_number(self) -> None:
        result = ensure_finite(
            "12.25",
            name="x",
        )

        self.assertEqual(
            result,
            12.25,
        )

    def test_nan_rejected(self) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            ensure_finite(
                math.nan,
                name="x",
            )

    def test_positive_infinity_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            ensure_finite(
                math.inf,
                name="x",
            )

    def test_negative_infinity_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            ensure_finite(
                -math.inf,
                name="x",
            )

    def test_boolean_rejected(self) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            ensure_finite(
                True,
                name="x",
            )

    def test_invalid_string_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            ensure_finite(
                "not-a-number",
                name="x",
            )


class ExceptionedificeTests(unittest.TestCase):
    def test_geometry_edifice(self) -> None:
        self.assertTrue(
            issubclass(
                InvalidGeometryError,
                GeometryError,
            )
        )

        self.assertTrue(
            issubclass(
                ArcGeometryError,
                GeometryError,
            )
        )

        self.assertTrue(
            issubclass(
                PathTopologyError,
                GeometryError,
            )
        )

    def test_transform_edifice(self) -> None:
        self.assertTrue(
            issubclass(
                InvalidTransformError,
                TransformError,
            )
        )

        self.assertTrue(
            issubclass(
                SingularTransformError,
                TransformError,
            )
        )

    def test_security_edifice(self) -> None:
        classes = (
            URLPolicyError,
            ScriptPolicyError,
            UnsafeMarkupError,
            EntityPolicyError,
            ExternalEntityError,
        )

        for error_type in classes:
            with self.subTest(
                error_type=error_type.__name__
            ):
                self.assertTrue(
                    issubclass(
                        error_type,
                        SecurityPolicyError,
                    )
                )

    def test_serialization_edifice(
        self,
    ) -> None:
        classes = (
            NumericSerializationError,
            XMLSerializationError,
            EscapingError,
            NamespaceError,
            ReferenceSerializationError,
        )

        for error_type in classes:
            with self.subTest(
                error_type=error_type.__name__
            ):
                self.assertTrue(
                    issubclass(
                        error_type,
                        SerializationError,
                    )
                )

    def test_persistence_edifice(self) -> None:
        classes = (
            DestinationPolicyError,
            PathTraversalError,
            AtomicWriteError,
            FsyncError,
            OutputIntegrityError,
        )

        for error_type in classes:
            with self.subTest(
                error_type=error_type.__name__
            ):
                self.assertTrue(
                    issubclass(
                        error_type,
                        PersistenceError,
                    )
                )

    def test_internal_error_is_fatal(self) -> None:
        error = InvariantViolationError(
            "impossible internal state"
        )

        diagnostic = error.to_diagnostic()

        self.assertEqual(
            diagnostic.severity,
            DiagnosticSeverity.FATAL,
        )

        self.assertTrue(
            isinstance(
                error,
                InternalVectorError,
            )
        )


class BroadTypeAvailabilityTests(
    unittest.TestCase
):
    """
    Smoke-test the specialized public error vocabulary.

    These assertions deliberately make sure later renderer modules can rely
    on the expected names without accidentally collapsing the taxonomy.
    """

    def test_validation_types(self) -> None:
        classes = (
            SceneValidationError,
            ConstructionValidationError,
            GraphValidationError,
            ProjectionValidationError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    DiagnosticError,
                )
            )

    def test_reference_types(self) -> None:
        classes = (
            ReferenceResolutionError,
            DuplicateIdentityError,
            DuplicateProjectionIdError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    VectorError,
                )
            )

    def test_filter_types(self) -> None:
        classes = (
            FilterGraphError,
            FilterDependencyError,
            FilterPrimitiveError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    VectorError,
                )
            )

    def test_resource_types(self) -> None:
        classes = (
            ResourcePolicyError,
            ResourceDigestError,
            ResourceSizeError,
            ExternalResourceUnavailableError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    VectorError,
                )
            )

    def test_compatibility_types(self) -> None:
        classes = (
            CompatibilityError,
            UnsupportedProfileError,
            UnsupportedFeatureError,
            UnknownFeatureError,
            CompatibilityDegradationError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    VectorError,
                )
            )

    def test_backend_types(self) -> None:
        classes = (
            BackendIntegrityError,
            GeometryBackendError,
            ShapingBackendError,
            RasterBackendError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    VectorError,
                )
            )

    def test_schema_types(self) -> None:
        classes = (
            SchemaVersionError,
            SceneSchemaError,
            SchemaMigrationError,
        )

        for error_type in classes:
            self.assertTrue(
                issubclass(
                    error_type,
                    VectorError,
                )
            )

    def test_cache_type(self) -> None:
        self.assertTrue(
            issubclass(
                CacheIntegrityError,
                VectorError,
            )
        )


class HelperTests(unittest.TestCase):
    def test_report_from(self) -> None:
        report = report_from(
            (
                Diagnostic.info(
                    "proof.info",
                    "proof information",
                ),
            ),
            phase="helper-proof",
        )

        self.assertTrue(
            report.ok
        )

        self.assertEqual(
            report.phase,
            "helper-proof",
        )

    def test_raise_for_report_type_guard(
        self,
    ) -> None:
        report = DiagnosticReport(
            phase="type-guard"
        )

        with self.assertRaises(
            TypeError
        ):
            raise_for_report(
                report,
                error_type=VectorError,
            )


def main() -> int:
    print(
        "SAVANT Filament Vector Renderer"
    )

    print(
        "errors.py self-test"
    )

    print(
        f"module version: {MODULE_VERSION}"
    )

    print()

    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__)
    )

    runner = unittest.TextTestRunner(
        verbosity=2
    )

    result = runner.run(
        suite
    )

    print()

    if result.wasSuccessful():
        print(
            "ALL ERRORS.PY PROOFS PASSED"
        )
        return 0

    print(
        "ERRORS.PY PROOF FAILURE"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
