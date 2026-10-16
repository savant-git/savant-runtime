"""
SAVANT Filament Vector Renderer
Comprehensive geometry.py self-test suite.

This suite verifies the native deterministic geometry kernel used by the
Filament vector renderer.

The tests deliberately cover both positive behavior and rejection behavior:

* finite-number and tolerance policy;
* points and vectors;
* bounds and intersections;
* affine transform algebra and multiplication order;
* inverse and singular transforms;
* uniform-similarity detection;
* line geometry;
* quadratic Bézier evaluation, extrema, bounds, subdivision and length;
* cubic Bézier evaluation, extrema, bounds, subdivision and length;
* SVG elliptical-arc endpoint-to-center conversion;
* exact preservation of canonical arc endpoints;
* arc extrema and rotated-ellipse bounds;
* arc length and tangent calculations;
* deterministic arc-to-cubic approximation;
* canonical path topology;
* compound subpaths and ClosePath semantics;
* path bounds and length;
* point-at-length and tangent-at-length;
* deterministic path normalization;
* exact and approximation-bearing affine path transformation;
* curve and path flattening;
* conservative stroke-aware bounds;
* explicit refusal of unsupported general boolean/offset/stroke expansion;
* native backend protocol identity;
* schema and public-kernel invariants.

No third-party test framework is required.

Run with:

    python3 test_geometry.py

or:

    python3 -m unittest -v test_geometry.py
"""

from __future__ import annotations

import math
import unittest

from errors import (
    BoundsError,
    DegenerateGeometryError,
    InvalidGeometryError,
    NonFiniteGeometryError,
    PathGeometryError,
    PathTopologyError,
    SingularTransformError,
    UnsupportedFeatureError,
)

from geometry import (
    DEFAULT_TOLERANCE,
    GEOMETRY_SCHEMA,
    HALF_PI,
    IDENTITY_TRANSFORM,
    MODULE_VERSION,
    NATIVE_GEOMETRY_BACKEND,
    ORIGIN,
    PATH_SCHEMA,
    PI,
    TAU,
    ZERO_VECTOR,
    AffineTransform,
    ApproximationRecord,
    ArcBezierApproximation,
    ArcCenterParameters,
    ArcTo,
    BooleanOperation,
    Bounds,
    ClosePath,
    CubicBezierSegment,
    CubicTo,
    EllipticalArcSegment,
    FillRule,
    FlattenedPath,
    FlattenedSubpath,
    GeometryBackend,
    LineSegment,
    LineTo,
    MoveTo,
    NativeGeometryBackend,
    Path,
    PathTransformResult,
    Point,
    QuadraticBezierSegment,
    QuadraticTo,
    Segment,
    SegmentRecord,
    StrokeLineCap,
    StrokeLineJoin,
    TolerancePolicy,
    Vector,
    arc_to_cubic_beziers,
    clamp,
    flatten_path,
    flatten_segment,
    lerp_scalar,
    normalize_angle_radians,
    normalize_degrees,
    normalize_zero,
    stroke_aware_bounds,
    union_bounds,
)


class GeometryAssertions(unittest.TestCase):
    """
    Common precision-aware assertions for geometry tests.
    """

    def assertFloatAlmostEqual(
        self,
        actual: float,
        expected: float,
        *,
        places: int = 9,
        message: str | None = None,
    ) -> None:
        self.assertAlmostEqual(
            actual,
            expected,
            places=places,
            msg=message,
        )

    def assertPointAlmostEqual(
        self,
        actual: Point,
        expected: Point,
        *,
        places: int = 9,
    ) -> None:
        self.assertIsInstance(
            actual,
            Point,
        )

        self.assertFloatAlmostEqual(
            actual.x,
            expected.x,
            places=places,
        )

        self.assertFloatAlmostEqual(
            actual.y,
            expected.y,
            places=places,
        )

    def assertVectorAlmostEqual(
        self,
        actual: Vector,
        expected: Vector,
        *,
        places: int = 9,
    ) -> None:
        self.assertIsInstance(
            actual,
            Vector,
        )

        self.assertFloatAlmostEqual(
            actual.x,
            expected.x,
            places=places,
        )

        self.assertFloatAlmostEqual(
            actual.y,
            expected.y,
            places=places,
        )

    def assertBoundsAlmostEqual(
        self,
        actual: Bounds,
        expected: Bounds,
        *,
        places: int = 9,
    ) -> None:
        self.assertFloatAlmostEqual(
            actual.min_x,
            expected.min_x,
            places=places,
        )

        self.assertFloatAlmostEqual(
            actual.min_y,
            expected.min_y,
            places=places,
        )

        self.assertFloatAlmostEqual(
            actual.max_x,
            expected.max_x,
            places=places,
        )

        self.assertFloatAlmostEqual(
            actual.max_y,
            expected.max_y,
            places=places,
        )

    def assertPointInsideBounds(
        self,
        point: Point,
        bounds: Bounds,
        *,
        epsilon: float = 1.0e-8,
    ) -> None:
        self.assertGreaterEqual(
            point.x,
            bounds.min_x - epsilon,
        )

        self.assertLessEqual(
            point.x,
            bounds.max_x + epsilon,
        )

        self.assertGreaterEqual(
            point.y,
            bounds.min_y - epsilon,
        )

        self.assertLessEqual(
            point.y,
            bounds.max_y + epsilon,
        )


class SchemaIdentityTests(
    GeometryAssertions
):
    def test_geometry_schema(self) -> None:
        self.assertEqual(
            GEOMETRY_SCHEMA,
            "savant://filament/vector/geometry/1.0.0",
        )

    def test_path_schema(self) -> None:
        self.assertEqual(
            PATH_SCHEMA,
            "savant://filament/vector/path/1.0.0",
        )

    def test_module_version(self) -> None:
        self.assertEqual(
            MODULE_VERSION,
            "1.0.0",
        )

    def test_mathematical_constants(self) -> None:
        self.assertFloatAlmostEqual(
            PI,
            math.pi,
        )

        self.assertFloatAlmostEqual(
            TAU,
            math.tau,
        )

        self.assertFloatAlmostEqual(
            HALF_PI,
            math.pi / 2.0,
        )


class NumericPolicyTests(
    GeometryAssertions
):
    def test_normalize_negative_zero(self) -> None:
        value = normalize_zero(
            -0.0
        )

        self.assertEqual(
            value,
            0.0,
        )

        self.assertEqual(
            math.copysign(
                1.0,
                value,
            ),
            1.0,
        )

    def test_clamp_lower(self) -> None:
        self.assertEqual(
            clamp(
                -10.0,
                0.0,
                1.0,
            ),
            0.0,
        )

    def test_clamp_middle(self) -> None:
        self.assertEqual(
            clamp(
                0.25,
                0.0,
                1.0,
            ),
            0.25,
        )

    def test_clamp_upper(self) -> None:
        self.assertEqual(
            clamp(
                10.0,
                0.0,
                1.0,
            ),
            1.0,
        )

    def test_clamp_rejects_reversed_interval(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            clamp(
                1.0,
                2.0,
                1.0,
            )

    def test_scalar_lerp(self) -> None:
        self.assertFloatAlmostEqual(
            lerp_scalar(
                10.0,
                20.0,
                0.25,
            ),
            12.5,
        )

    def test_angle_normalization(self) -> None:
        self.assertFloatAlmostEqual(
            normalize_angle_radians(
                TAU + HALF_PI
            ),
            HALF_PI,
        )

    def test_degree_normalization_positive(
        self,
    ) -> None:
        self.assertFloatAlmostEqual(
            normalize_degrees(
                450.0
            ),
            90.0,
        )

    def test_degree_normalization_negative(
        self,
    ) -> None:
        self.assertFloatAlmostEqual(
            normalize_degrees(
                -450.0
            ),
            -90.0,
        )

    def test_point_rejects_nan(self) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            Point(
                math.nan,
                0.0,
            )

    def test_point_rejects_infinity(
        self,
    ) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            Point(
                math.inf,
                0.0,
            )

    def test_vector_rejects_boolean(
        self,
    ) -> None:
        with self.assertRaises(
            NonFiniteGeometryError
        ):
            Vector(
                True,
                0.0,
            )


class TolerancePolicyTests(
    GeometryAssertions
):
    def test_default_policy(self) -> None:
        self.assertGreater(
            DEFAULT_TOLERANCE.epsilon,
            0.0,
        )

        self.assertGreater(
            DEFAULT_TOLERANCE.length_tolerance,
            0.0,
        )

        self.assertGreater(
            DEFAULT_TOLERANCE.flattening_tolerance,
            0.0,
        )

    def test_near_zero(self) -> None:
        self.assertTrue(
            DEFAULT_TOLERANCE.near_zero(
                1.0e-13
            )
        )

    def test_not_near_zero(self) -> None:
        self.assertFalse(
            DEFAULT_TOLERANCE.near_zero(
                1.0e-4
            )
        )

    def test_scale_aware_close(self) -> None:
        policy = TolerancePolicy(
            epsilon=1.0e-9
        )

        self.assertTrue(
            policy.close(
                1_000_000.0,
                1_000_000.0005,
            )
        )

    def test_zero_epsilon_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            InvalidGeometryError
        ):
            TolerancePolicy(
                epsilon=0.0
            )

    def test_invalid_depth_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            InvalidGeometryError
        ):
            TolerancePolicy(
                max_integration_depth=0
            )

    def test_boolean_depth_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            InvalidGeometryError
        ):
            TolerancePolicy(
                max_integration_depth=True
            )


class PointVectorTests(
    GeometryAssertions
):
    def test_origin_constant(self) -> None:
        self.assertEqual(
            ORIGIN,
            Point(
                0.0,
                0.0,
            ),
        )

    def test_zero_vector_constant(self) -> None:
        self.assertEqual(
            ZERO_VECTOR,
            Vector(
                0.0,
                0.0,
            ),
        )

    def test_point_minus_point(self) -> None:
        result = (
            Point(
                5.0,
                8.0,
            )
            - Point(
                2.0,
                3.0,
            )
        )

        self.assertEqual(
            result,
            Vector(
                3.0,
                5.0,
            ),
        )

    def test_point_plus_vector(self) -> None:
        result = (
            Point(
                1.0,
                2.0,
            )
            + Vector(
                3.0,
                4.0,
            )
        )

        self.assertEqual(
            result,
            Point(
                4.0,
                6.0,
            ),
        )

    def test_point_minus_vector(self) -> None:
        result = (
            Point(
                4.0,
                6.0,
            )
            - Vector(
                3.0,
                4.0,
            )
        )

        self.assertEqual(
            result,
            Point(
                1.0,
                2.0,
            ),
        )

    def test_vector_addition(self) -> None:
        result = (
            Vector(
                1.0,
                2.0,
            )
            + Vector(
                3.0,
                4.0,
            )
        )

        self.assertEqual(
            result,
            Vector(
                4.0,
                6.0,
            ),
        )

    def test_vector_subtraction(self) -> None:
        result = (
            Vector(
                5.0,
                6.0,
            )
            - Vector(
                1.0,
                2.0,
            )
        )

        self.assertEqual(
            result,
            Vector(
                4.0,
                4.0,
            ),
        )

    def test_vector_negation(self) -> None:
        self.assertEqual(
            -Vector(
                2.0,
                -3.0,
            ),
            Vector(
                -2.0,
                3.0,
            ),
        )

    def test_vector_scalar_multiply(
        self,
    ) -> None:
        self.assertEqual(
            Vector(
                2.0,
                3.0,
            )
            * 4.0,
            Vector(
                8.0,
                12.0,
            ),
        )

    def test_vector_reverse_scalar_multiply(
        self,
    ) -> None:
        self.assertEqual(
            4.0
            * Vector(
                2.0,
                3.0,
            ),
            Vector(
                8.0,
                12.0,
            ),
        )

    def test_vector_scalar_division(
        self,
    ) -> None:
        self.assertEqual(
            Vector(
                8.0,
                12.0,
            )
            / 4.0,
            Vector(
                2.0,
                3.0,
            ),
        )

    def test_vector_division_by_zero(
        self,
    ) -> None:
        with self.assertRaises(
            DegenerateGeometryError
        ):
            Vector(
                1.0,
                2.0,
            ) / 0.0

    def test_dot_product(self) -> None:
        self.assertEqual(
            Vector(
                1.0,
                2.0,
            ).dot(
                Vector(
                    3.0,
                    4.0,
                )
            ),
            11.0,
        )

    def test_cross_product(self) -> None:
        self.assertEqual(
            Vector(
                1.0,
                0.0,
            ).cross(
                Vector(
                    0.0,
                    1.0,
                )
            ),
            1.0,
        )

    def test_vector_magnitude(self) -> None:
        vector = Vector(
            3.0,
            4.0,
        )

        self.assertEqual(
            vector.magnitude_squared,
            25.0,
        )

        self.assertEqual(
            vector.magnitude,
            5.0,
        )

    def test_vector_normalization(
        self,
    ) -> None:
        normalized = Vector(
            3.0,
            4.0,
        ).normalized()

        self.assertVectorAlmostEqual(
            normalized,
            Vector(
                0.6,
                0.8,
            ),
        )

    def test_zero_vector_normalization_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            DegenerateGeometryError
        ):
            ZERO_VECTOR.normalized()

    def test_perpendicular_left(self) -> None:
        self.assertEqual(
            Vector(
                3.0,
                4.0,
            ).perpendicular_left(),
            Vector(
                -4.0,
                3.0,
            ),
        )

    def test_perpendicular_right(self) -> None:
        self.assertEqual(
            Vector(
                3.0,
                4.0,
            ).perpendicular_right(),
            Vector(
                4.0,
                -3.0,
            ),
        )

    def test_point_distance(self) -> None:
        first = Point(
            0.0,
            0.0,
        )

        second = Point(
            3.0,
            4.0,
        )

        self.assertEqual(
            first.distance_to(
                second
            ),
            5.0,
        )

        self.assertEqual(
            first.distance_squared_to(
                second
            ),
            25.0,
        )

    def test_point_lerp(self) -> None:
        result = Point(
            0.0,
            0.0,
        ).lerp(
            Point(
                10.0,
                20.0,
            ),
            0.25,
        )

        self.assertEqual(
            result,
            Point(
                2.5,
                5.0,
            ),
        )


class BoundsTests(
    GeometryAssertions
):
    def test_from_point(self) -> None:
        bounds = Bounds.from_point(
            Point(
                2.0,
                3.0,
            )
        )

        self.assertEqual(
            bounds.width,
            0.0,
        )

        self.assertEqual(
            bounds.height,
            0.0,
        )

    def test_from_points(self) -> None:
        bounds = Bounds.from_points(
            (
                Point(
                    -2.0,
                    5.0,
                ),
                Point(
                    10.0,
                    -4.0,
                ),
                Point(
                    4.0,
                    8.0,
                ),
            )
        )

        self.assertEqual(
            bounds,
            Bounds(
                -2.0,
                -4.0,
                10.0,
                8.0,
            ),
        )

    def test_empty_point_sequence_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            BoundsError
        ):
            Bounds.from_points(
                ()
            )

    def test_invalid_horizontal_bounds(
        self,
    ) -> None:
        with self.assertRaises(
            BoundsError
        ):
            Bounds(
                10.0,
                0.0,
                0.0,
                10.0,
            )

    def test_invalid_vertical_bounds(
        self,
    ) -> None:
        with self.assertRaises(
            BoundsError
        ):
            Bounds(
                0.0,
                10.0,
                10.0,
                0.0,
            )

    def test_center(self) -> None:
        bounds = Bounds(
            0.0,
            0.0,
            10.0,
            20.0,
        )

        self.assertEqual(
            bounds.center,
            Point(
                5.0,
                10.0,
            ),
        )

    def test_corners(self) -> None:
        bounds = Bounds(
            1.0,
            2.0,
            5.0,
            7.0,
        )

        self.assertEqual(
            bounds.corners,
            (
                Point(
                    1.0,
                    2.0,
                ),
                Point(
                    5.0,
                    2.0,
                ),
                Point(
                    5.0,
                    7.0,
                ),
                Point(
                    1.0,
                    7.0,
                ),
            ),
        )

    def test_contains_point(self) -> None:
        bounds = Bounds(
            0.0,
            0.0,
            10.0,
            10.0,
        )

        self.assertTrue(
            bounds.contains_point(
                Point(
                    5.0,
                    5.0,
                )
            )
        )

        self.assertFalse(
            bounds.contains_point(
                Point(
                    11.0,
                    5.0,
                )
            )
        )

    def test_union(self) -> None:
        first = Bounds(
            0.0,
            0.0,
            10.0,
            10.0,
        )

        second = Bounds(
            5.0,
            -5.0,
            20.0,
            5.0,
        )

        self.assertEqual(
            first.union(
                second
            ),
            Bounds(
                0.0,
                -5.0,
                20.0,
                10.0,
            ),
        )

    def test_intersection(self) -> None:
        first = Bounds(
            0.0,
            0.0,
            10.0,
            10.0,
        )

        second = Bounds(
            5.0,
            5.0,
            20.0,
            20.0,
        )

        self.assertEqual(
            first.intersection(
                second
            ),
            Bounds(
                5.0,
                5.0,
                10.0,
                10.0,
            ),
        )

    def test_disjoint_intersection(self) -> None:
        first = Bounds(
            0.0,
            0.0,
            1.0,
            1.0,
        )

        second = Bounds(
            2.0,
            2.0,
            3.0,
            3.0,
        )

        self.assertIsNone(
            first.intersection(
                second
            )
        )

    def test_expanded(self) -> None:
        bounds = Bounds(
            0.0,
            0.0,
            10.0,
            20.0,
        ).expanded(
            2.0,
            3.0,
        )

        self.assertEqual(
            bounds,
            Bounds(
                -2.0,
                -3.0,
                12.0,
                23.0,
            ),
        )

    def test_translated(self) -> None:
        bounds = Bounds(
            0.0,
            0.0,
            10.0,
            10.0,
        ).translated(
            Vector(
                5.0,
                -2.0,
            )
        )

        self.assertEqual(
            bounds,
            Bounds(
                5.0,
                -2.0,
                15.0,
                8.0,
            ),
        )

    def test_union_bounds_empty(self) -> None:
        self.assertIsNone(
            union_bounds(
                ()
            )
        )

    def test_union_bounds_multiple(self) -> None:
        result = union_bounds(
            (
                Bounds(
                    0.0,
                    0.0,
                    1.0,
                    1.0,
                ),
                Bounds(
                    -5.0,
                    2.0,
                    3.0,
                    8.0,
                ),
                Bounds(
                    9.0,
                    -4.0,
                    12.0,
                    4.0,
                ),
            )
        )

        self.assertEqual(
            result,
            Bounds(
                -5.0,
                -4.0,
                12.0,
                8.0,
            ),
        )


class AffineTransformTests(
    GeometryAssertions
):
    def test_identity(self) -> None:
        point = Point(
            12.0,
            -8.0,
        )

        self.assertPointAlmostEqual(
            IDENTITY_TRANSFORM.apply_point(
                point
            ),
            point,
        )

        self.assertTrue(
            IDENTITY_TRANSFORM.is_identity()
        )

    def test_translation(self) -> None:
        transform = (
            AffineTransform.translate(
                10.0,
                -5.0,
            )
        )

        result = transform.apply_point(
            Point(
                1.0,
                2.0,
            )
        )

        self.assertEqual(
            result,
            Point(
                11.0,
                -3.0,
            ),
        )

    def test_translation_does_not_affect_vector(
        self,
    ) -> None:
        transform = (
            AffineTransform.translate(
                100.0,
                200.0,
            )
        )

        vector = transform.apply_vector(
            Vector(
                3.0,
                4.0,
            )
        )

        self.assertEqual(
            vector,
            Vector(
                3.0,
                4.0,
            ),
        )

    def test_uniform_scale(self) -> None:
        transform = (
            AffineTransform.scale(
                2.0
            )
        )

        self.assertEqual(
            transform.apply_point(
                Point(
                    3.0,
                    4.0,
                )
            ),
            Point(
                6.0,
                8.0,
            ),
        )

    def test_nonuniform_scale(self) -> None:
        transform = (
            AffineTransform.scale(
                2.0,
                3.0,
            )
        )

        self.assertEqual(
            transform.apply_point(
                Point(
                    3.0,
                    4.0,
                )
            ),
            Point(
                6.0,
                12.0,
            ),
        )

    def test_rotation_90(self) -> None:
        transform = (
            AffineTransform.rotate(
                90.0
            )
        )

        result = transform.apply_point(
            Point(
                1.0,
                0.0,
            )
        )

        self.assertPointAlmostEqual(
            result,
            Point(
                0.0,
                1.0,
            ),
        )

    def test_rotate_about(self) -> None:
        transform = (
            AffineTransform.rotate_about(
                180.0,
                Point(
                    10.0,
                    10.0,
                ),
            )
        )

        result = transform.apply_point(
            Point(
                15.0,
                10.0,
            )
        )

        self.assertPointAlmostEqual(
            result,
            Point(
                5.0,
                10.0,
            ),
        )

    def test_skew_x(self) -> None:
        transform = (
            AffineTransform.skew_x(
                45.0
            )
        )

        result = transform.apply_point(
            Point(
                0.0,
                2.0,
            )
        )

        self.assertPointAlmostEqual(
            result,
            Point(
                2.0,
                2.0,
            ),
        )

    def test_skew_y(self) -> None:
        transform = (
            AffineTransform.skew_y(
                45.0
            )
        )

        result = transform.apply_point(
            Point(
                2.0,
                0.0,
            )
        )

        self.assertPointAlmostEqual(
            result,
            Point(
                2.0,
                2.0,
            ),
        )

    def test_matrix_composition_order(
        self,
    ) -> None:
        translate = (
            AffineTransform.translate(
                10.0,
                0.0,
            )
        )

        scale = (
            AffineTransform.scale(
                2.0
            )
        )

        composed = (
            translate
            @ scale
        )

        result = composed.apply_point(
            Point(
                1.0,
                0.0,
            )
        )

        self.assertPointAlmostEqual(
            result,
            Point(
                12.0,
                0.0,
            ),
        )

    def test_then_operation_order(self) -> None:
        translate = (
            AffineTransform.translate(
                10.0,
                0.0,
            )
        )

        scale = (
            AffineTransform.scale(
                2.0
            )
        )

        composed = translate.then(
            scale
        )

        result = composed.apply_point(
            Point(
                1.0,
                0.0,
            )
        )

        self.assertPointAlmostEqual(
            result,
            Point(
                22.0,
                0.0,
            ),
        )

    def test_determinant(self) -> None:
        transform = (
            AffineTransform.scale(
                2.0,
                3.0,
            )
        )

        self.assertEqual(
            transform.determinant,
            6.0,
        )

    def test_inverse(self) -> None:
        transform = (
            AffineTransform.translate(
                20.0,
                -4.0,
            )
            @ AffineTransform.rotate(
                33.0
            )
            @ AffineTransform.scale(
                2.0,
                3.0,
            )
        )

        inverse = transform.inverse()

        original = Point(
            7.5,
            -11.0,
        )

        projected = (
            transform.apply_point(
                original
            )
        )

        restored = (
            inverse.apply_point(
                projected
            )
        )

        self.assertPointAlmostEqual(
            restored,
            original,
            places=8,
        )

    def test_singular_inverse_rejected(
        self,
    ) -> None:
        transform = (
            AffineTransform.scale(
                0.0,
                1.0,
            )
        )

        self.assertTrue(
            transform.is_singular()
        )

        with self.assertRaises(
            SingularTransformError
        ):
            transform.inverse()

    def test_apply_bounds(self) -> None:
        bounds = Bounds(
            0.0,
            0.0,
            10.0,
            20.0,
        )

        transform = (
            AffineTransform.translate(
                5.0,
                7.0,
            )
        )

        self.assertEqual(
            transform.apply_bounds(
                bounds
            ),
            Bounds(
                5.0,
                7.0,
                15.0,
                27.0,
            ),
        )

    def test_uniform_similarity_identity(
        self,
    ) -> None:
        result = (
            AffineTransform.identity()
            .positive_uniform_similarity()
        )

        self.assertIsNotNone(
            result
        )

        scale, rotation = result

        self.assertFloatAlmostEqual(
            scale,
            1.0,
        )

        self.assertFloatAlmostEqual(
            rotation,
            0.0,
        )

    def test_uniform_similarity_rotation_scale(
        self,
    ) -> None:
        transform = (
            AffineTransform.rotate(
                30.0
            )
            @ AffineTransform.scale(
                4.0
            )
        )

        result = (
            transform
            .positive_uniform_similarity()
        )

        self.assertIsNotNone(
            result
        )

        scale, rotation = result

        self.assertFloatAlmostEqual(
            scale,
            4.0,
            places=8,
        )

        self.assertFloatAlmostEqual(
            rotation,
            30.0,
            places=8,
        )

    def test_nonuniform_scale_is_not_similarity(
        self,
    ) -> None:
        result = (
            AffineTransform.scale(
                2.0,
                3.0,
            )
            .positive_uniform_similarity()
        )

        self.assertIsNone(
            result
        )

    def test_reflection_is_not_positive_similarity(
        self,
    ) -> None:
        result = (
            AffineTransform.scale(
                -1.0,
                1.0,
            )
            .positive_uniform_similarity()
        )

        self.assertIsNone(
            result
        )

    def test_skew_is_not_similarity(self) -> None:
        result = (
            AffineTransform.skew_x(
                10.0
            )
            .positive_uniform_similarity()
        )

        self.assertIsNone(
            result
        )


class LineSegmentTests(
    GeometryAssertions
):
    def setUp(self) -> None:
        self.segment = LineSegment(
            Point(
                0.0,
                0.0,
            ),
            Point(
                3.0,
                4.0,
            ),
        )

    def test_segment_protocol(self) -> None:
        self.assertIsInstance(
            self.segment,
            Segment,
        )

    def test_point_at_zero(self) -> None:
        self.assertEqual(
            self.segment.point_at(
                0.0
            ),
            self.segment.start,
        )

    def test_point_at_one(self) -> None:
        self.assertEqual(
            self.segment.point_at(
                1.0
            ),
            self.segment.end,
        )

    def test_point_at_half(self) -> None:
        self.assertEqual(
            self.segment.point_at(
                0.5
            ),
            Point(
                1.5,
                2.0,
            ),
        )

    def test_derivative(self) -> None:
        self.assertEqual(
            self.segment.derivative_at(
                0.25
            ),
            Vector(
                3.0,
                4.0,
            ),
        )

    def test_tangent(self) -> None:
        self.assertVectorAlmostEqual(
            self.segment.tangent_at(
                0.5
            ),
            Vector(
                0.6,
                0.8,
            ),
        )

    def test_length(self) -> None:
        self.assertEqual(
            self.segment.length(),
            5.0,
        )

    def test_length_to(self) -> None:
        self.assertEqual(
            self.segment.length_to(
                0.4
            ),
            2.0,
        )

    def test_bounds(self) -> None:
        self.assertEqual(
            self.segment.bounds(),
            Bounds(
                0.0,
                0.0,
                3.0,
                4.0,
            ),
        )

    def test_subdivide(self) -> None:
        left, right = (
            self.segment.subdivide(
                0.5
            )
        )

        self.assertEqual(
            left.end,
            right.start,
        )

        self.assertPointAlmostEqual(
            left.end,
            Point(
                1.5,
                2.0,
            ),
        )

        self.assertFloatAlmostEqual(
            left.length()
            + right.length(),
            self.segment.length(),
        )

    def test_parameter_outside_unit_interval(
        self,
    ) -> None:
        with self.assertRaises(
            InvalidGeometryError
        ):
            self.segment.point_at(
                1.1
            )


class QuadraticBezierTests(
    GeometryAssertions
):
    def setUp(self) -> None:
        self.curve = (
            QuadraticBezierSegment(
                start=Point(
                    0.0,
                    0.0,
                ),
                control=Point(
                    50.0,
                    100.0,
                ),
                end=Point(
                    100.0,
                    0.0,
                ),
            )
        )

    def test_endpoints(self) -> None:
        self.assertEqual(
            self.curve.point_at(
                0.0
            ),
            self.curve.start,
        )

        self.assertEqual(
            self.curve.point_at(
                1.0
            ),
            self.curve.end,
        )

    def test_midpoint(self) -> None:
        self.assertPointAlmostEqual(
            self.curve.point_at(
                0.5
            ),
            Point(
                50.0,
                50.0,
            ),
        )

    def test_derivative_start(self) -> None:
        self.assertVectorAlmostEqual(
            self.curve.derivative_at(
                0.0
            ),
            Vector(
                100.0,
                200.0,
            ),
        )

    def test_derivative_end(self) -> None:
        self.assertVectorAlmostEqual(
            self.curve.derivative_at(
                1.0
            ),
            Vector(
                100.0,
                -200.0,
            ),
        )

    def test_extrema_parameters(self) -> None:
        extrema = (
            self.curve
            .extrema_parameters()
        )

        self.assertEqual(
            len(extrema),
            1,
        )

        self.assertFloatAlmostEqual(
            extrema[0],
            0.5,
        )

    def test_exact_bounds(self) -> None:
        bounds = self.curve.bounds()

        self.assertBoundsAlmostEqual(
            bounds,
            Bounds(
                0.0,
                0.0,
                100.0,
                50.0,
            ),
        )

    def test_length_exceeds_chord(self) -> None:
        chord = (
            self.curve.start
            .distance_to(
                self.curve.end
            )
        )

        self.assertGreater(
            self.curve.length(),
            chord,
        )

    def test_length_to_half(self) -> None:
        first_half = (
            self.curve.length_to(
                0.5
            )
        )

        total = self.curve.length()

        self.assertFloatAlmostEqual(
            first_half,
            total / 2.0,
            places=6,
        )

    def test_subdivision_continuity(
        self,
    ) -> None:
        left, right = (
            self.curve.subdivide(
                0.5
            )
        )

        self.assertPointAlmostEqual(
            left.end,
            right.start,
        )

        self.assertPointAlmostEqual(
            left.end,
            self.curve.point_at(
                0.5
            ),
        )

        self.assertFloatAlmostEqual(
            (
                left.length()
                + right.length()
            ),
            self.curve.length(),
            places=6,
        )


class CubicBezierTests(
    GeometryAssertions
):
    def setUp(self) -> None:
        self.curve = (
            CubicBezierSegment(
                start=Point(
                    0.0,
                    0.0,
                ),
                control1=Point(
                    0.0,
                    100.0,
                ),
                control2=Point(
                    100.0,
                    100.0,
                ),
                end=Point(
                    100.0,
                    0.0,
                ),
            )
        )

    def test_endpoints(self) -> None:
        self.assertEqual(
            self.curve.point_at(
                0.0
            ),
            self.curve.start,
        )

        self.assertEqual(
            self.curve.point_at(
                1.0
            ),
            self.curve.end,
        )

    def test_midpoint(self) -> None:
        self.assertPointAlmostEqual(
            self.curve.point_at(
                0.5
            ),
            Point(
                50.0,
                75.0,
            ),
        )

    def test_extrema_contains_midpoint(
        self,
    ) -> None:
        extrema = (
            self.curve
            .extrema_parameters()
        )

        self.assertTrue(
            any(
                abs(
                    value - 0.5
                )
                < 1.0e-9
                for value
                in extrema
            )
        )

    def test_exact_bounds(self) -> None:
        bounds = self.curve.bounds()

        self.assertBoundsAlmostEqual(
            bounds,
            Bounds(
                0.0,
                0.0,
                100.0,
                75.0,
            ),
        )

    def test_tangent_start(self) -> None:
        tangent = (
            self.curve.tangent_at(
                0.0
            )
        )

        self.assertVectorAlmostEqual(
            tangent,
            Vector(
                0.0,
                1.0,
            ),
        )

    def test_tangent_end(self) -> None:
        tangent = (
            self.curve.tangent_at(
                1.0
            )
        )

        self.assertVectorAlmostEqual(
            tangent,
            Vector(
                0.0,
                -1.0,
            ),
        )

    def test_length_exceeds_chord(self) -> None:
        self.assertGreater(
            self.curve.length(),
            self.curve.start.distance_to(
                self.curve.end
            ),
        )

    def test_symmetric_half_length(self) -> None:
        total = self.curve.length()

        half = self.curve.length_to(
            0.5
        )

        self.assertFloatAlmostEqual(
            half,
            total / 2.0,
            places=6,
        )

    def test_subdivision_continuity(
        self,
    ) -> None:
        left, right = (
            self.curve.subdivide(
                0.5
            )
        )

        self.assertPointAlmostEqual(
            left.end,
            right.start,
        )

        self.assertPointAlmostEqual(
            left.end,
            self.curve.point_at(
                0.5
            ),
        )

        self.assertFloatAlmostEqual(
            (
                left.length()
                + right.length()
            ),
            self.curve.length(),
            places=6,
        )


class EllipticalArcTests(
    GeometryAssertions
):
    def make_quarter_circle(
        self,
    ) -> EllipticalArcSegment:
        return EllipticalArcSegment(
            start=Point(
                1.0,
                0.0,
            ),
            rx=1.0,
            ry=1.0,
            x_axis_rotation=0.0,
            large_arc=False,
            sweep=True,
            end=Point(
                0.0,
                1.0,
            ),
        )

    def test_center_conversion_quarter_circle(
        self,
    ) -> None:
        arc = self.make_quarter_circle()

        center = (
            arc.center_parameters()
        )

        self.assertPointAlmostEqual(
            center.center,
            Point(
                0.0,
                0.0,
            ),
            places=8,
        )

        self.assertFloatAlmostEqual(
            center.rx,
            1.0,
        )

        self.assertFloatAlmostEqual(
            center.ry,
            1.0,
        )

        self.assertFloatAlmostEqual(
            center.delta_angle,
            HALF_PI,
            places=8,
        )

    def test_quarter_circle_midpoint(
        self,
    ) -> None:
        arc = self.make_quarter_circle()

        expected = math.sqrt(
            0.5
        )

        point = arc.point_at(
            0.5
        )

        self.assertPointAlmostEqual(
            point,
            Point(
                expected,
                expected,
            ),
            places=8,
        )

    def test_quarter_circle_bounds(
        self,
    ) -> None:
        arc = self.make_quarter_circle()

        self.assertBoundsAlmostEqual(
            arc.bounds(),
            Bounds(
                0.0,
                0.0,
                1.0,
                1.0,
            ),
            places=8,
        )

    def test_quarter_circle_length(
        self,
    ) -> None:
        arc = self.make_quarter_circle()

        self.assertFloatAlmostEqual(
            arc.length(),
            HALF_PI,
            places=7,
        )

    def test_quarter_circle_start_tangent(
        self,
    ) -> None:
        arc = self.make_quarter_circle()

        tangent = arc.tangent_at(
            0.0
        )

        self.assertVectorAlmostEqual(
            tangent,
            Vector(
                0.0,
                1.0,
            ),
            places=8,
        )

    def test_zero_radius_is_line_like(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                0.0,
                0.0,
            ),
            rx=0.0,
            ry=10.0,
            x_axis_rotation=0.0,
            large_arc=False,
            sweep=False,
            end=Point(
                10.0,
                0.0,
            ),
        )

        self.assertTrue(
            arc.is_line_like()
        )

        self.assertPointAlmostEqual(
            arc.point_at(
                0.5
            ),
            Point(
                5.0,
                0.0,
            ),
        )

        self.assertFloatAlmostEqual(
            arc.length(),
            10.0,
        )

    def test_zero_length_arc(self) -> None:
        point = Point(
            3.0,
            4.0,
        )

        arc = EllipticalArcSegment(
            start=point,
            rx=10.0,
            ry=20.0,
            x_axis_rotation=45.0,
            large_arc=True,
            sweep=True,
            end=point,
        )

        self.assertTrue(
            arc.is_zero_length()
        )

        self.assertEqual(
            arc.length(),
            0.0,
        )

        self.assertEqual(
            arc.bounds(),
            Bounds.from_point(
                point
            ),
        )

        with self.assertRaises(
            DegenerateGeometryError
        ):
            arc.center_parameters()

    def test_radii_are_corrected_when_too_small(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                0.0,
                0.0,
            ),
            rx=1.0,
            ry=1.0,
            x_axis_rotation=0.0,
            large_arc=False,
            sweep=True,
            end=Point(
                10.0,
                0.0,
            ),
        )

        center = arc.center_parameters()

        self.assertGreaterEqual(
            center.rx,
            5.0 - 1.0e-9,
        )

    def test_large_arc_has_longer_length(
        self,
    ) -> None:
        short = (
            self.make_quarter_circle()
        )

        long_arc = EllipticalArcSegment(
            start=Point(
                1.0,
                0.0,
            ),
            rx=1.0,
            ry=1.0,
            x_axis_rotation=0.0,
            large_arc=True,
            sweep=True,
            end=Point(
                0.0,
                1.0,
            ),
        )

        self.assertGreater(
            long_arc.length(),
            short.length(),
        )

    def test_rotated_arc_preserves_exact_semantic_endpoints(
        self,
    ) -> None:
        start = Point(
            100.0,
            25.0,
        )

        end = Point(
            -40.0,
            75.0,
        )

        arc = EllipticalArcSegment(
            start=start,
            rx=90.0,
            ry=35.0,
            x_axis_rotation=37.0,
            large_arc=True,
            sweep=True,
            end=end,
        )

        self.assertIs(
            arc.point_at(
                0.0
            ),
            start,
        )

        self.assertIs(
            arc.point_at(
                1.0
            ),
            end,
        )

        self.assertEqual(
            arc.point_at(
                0.0
            ),
            start,
        )

        self.assertEqual(
            arc.point_at(
                1.0
            ),
            end,
        )

        bounds = arc.bounds()

        self.assertTrue(
            bounds.contains_point(
                start
            )
        )

        self.assertTrue(
            bounds.contains_point(
                end
            )
        )

    def test_rotated_arc_bounds_contain_samples(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                100.0,
                25.0,
            ),
            rx=90.0,
            ry=35.0,
            x_axis_rotation=37.0,
            large_arc=True,
            sweep=True,
            end=Point(
                -40.0,
                75.0,
            ),
        )

        bounds = arc.bounds()

        for index in range(
            1001
        ):
            parameter = (
                index / 1000.0
            )

            point = arc.point_at(
                parameter
            )

            self.assertPointInsideBounds(
                point,
                bounds,
                epsilon=1.0e-7,
            )

    def test_rotated_arc_bounds_are_finite(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                20.0,
                10.0,
            ),
            rx=60.0,
            ry=20.0,
            x_axis_rotation=75.0,
            large_arc=False,
            sweep=False,
            end=Point(
                -25.0,
                50.0,
            ),
        )

        bounds = arc.bounds()

        for value in (
            bounds.min_x,
            bounds.min_y,
            bounds.max_x,
            bounds.max_y,
        ):
            self.assertTrue(
                math.isfinite(
                    value
                )
            )


class ArcApproximationTests(
    GeometryAssertions
):
    def test_quarter_circle_approximation(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                1.0,
                0.0,
            ),
            rx=1.0,
            ry=1.0,
            x_axis_rotation=0.0,
            large_arc=False,
            sweep=True,
            end=Point(
                0.0,
                1.0,
            ),
        )

        approximation = (
            arc_to_cubic_beziers(
                arc,
                tolerance=1.0e-5,
            )
        )

        self.assertIsInstance(
            approximation,
            ArcBezierApproximation,
        )

        self.assertGreaterEqual(
            len(
                approximation.segments
            ),
            1,
        )

        self.assertPointAlmostEqual(
            approximation
            .segments[0]
            .start,
            arc.start,
            places=8,
        )

        self.assertPointAlmostEqual(
            approximation
            .segments[-1]
            .end,
            arc.end,
            places=8,
        )

    def test_approximation_segments_are_continuous(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                90.0,
                0.0,
            ),
            rx=90.0,
            ry=30.0,
            x_axis_rotation=25.0,
            large_arc=True,
            sweep=True,
            end=Point(
                -50.0,
                40.0,
            ),
        )

        approximation = (
            arc_to_cubic_beziers(
                arc,
                tolerance=1.0e-4,
            )
        )

        segments = (
            approximation.segments
        )

        for left, right in zip(
            segments,
            segments[1:],
        ):
            self.assertPointAlmostEqual(
                left.end,
                right.start,
                places=8,
            )

    def test_line_like_arc_approximation(
        self,
    ) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                0.0,
                0.0,
            ),
            rx=0.0,
            ry=10.0,
            x_axis_rotation=0.0,
            large_arc=False,
            sweep=True,
            end=Point(
                9.0,
                0.0,
            ),
        )

        result = arc_to_cubic_beziers(
            arc
        )

        self.assertEqual(
            len(result.segments),
            1,
        )

        cubic = result.segments[0]

        self.assertPointAlmostEqual(
            cubic.control1,
            Point(
                3.0,
                0.0,
            ),
        )

        self.assertPointAlmostEqual(
            cubic.control2,
            Point(
                6.0,
                0.0,
            ),
        )


class PathTopologyTests(
    GeometryAssertions
):
    def test_empty_path(self) -> None:
        path = Path()

        self.assertEqual(
            path.command_count,
            0,
        )

        self.assertEqual(
            path.subpath_count,
            0,
        )

        self.assertEqual(
            path.segment_count,
            0,
        )

        self.assertIsNone(
            path.bounds()
        )

        self.assertEqual(
            path.length(),
            0.0,
        )

    def test_drawing_before_move_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            PathTopologyError
        ):
            Path(
                commands=(
                    LineTo(
                        Point(
                            10.0,
                            10.0,
                        )
                    ),
                )
            )

    def test_invalid_command_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            PathGeometryError
        ):
            Path(
                commands=(
                    MoveTo(
                        Point(
                            0.0,
                            0.0,
                        )
                    ),
                    "not-a-command",
                )
            )

    def test_fill_rule_conversion(self) -> None:
        path = Path(
            commands=(),
            fill_rule="evenodd",
        )

        self.assertEqual(
            path.fill_rule,
            FillRule.EVENODD,
        )

    def test_basic_segments(self) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        0.0,
                    )
                ),
                QuadraticTo(
                    control=Point(
                        15.0,
                        10.0,
                    ),
                    end=Point(
                        20.0,
                        0.0,
                    ),
                ),
                CubicTo(
                    control1=Point(
                        25.0,
                        -10.0,
                    ),
                    control2=Point(
                        35.0,
                        10.0,
                    ),
                    end=Point(
                        40.0,
                        0.0,
                    ),
                ),
                ArcTo(
                    rx=10.0,
                    ry=5.0,
                    x_axis_rotation=15.0,
                    large_arc=False,
                    sweep=True,
                    end=Point(
                        55.0,
                        10.0,
                    ),
                ),
                ClosePath(),
            )
        )

        records = tuple(
            path.iter_segments()
        )

        self.assertEqual(
            len(records),
            5,
        )

        self.assertIsInstance(
            records[0].segment,
            LineSegment,
        )

        self.assertIsInstance(
            records[1].segment,
            QuadraticBezierSegment,
        )

        self.assertIsInstance(
            records[2].segment,
            CubicBezierSegment,
        )

        self.assertIsInstance(
            records[3].segment,
            EllipticalArcSegment,
        )

        self.assertTrue(
            records[4].closing
        )

    def test_compound_subpaths(self) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        0.0,
                    )
                ),
                MoveTo(
                    Point(
                        100.0,
                        100.0,
                    )
                ),
                LineTo(
                    Point(
                        110.0,
                        100.0,
                    )
                ),
            )
        )

        self.assertEqual(
            path.subpath_count,
            2,
        )

        records = tuple(
            path.iter_segments()
        )

        self.assertEqual(
            records[0].subpath_index,
            0,
        )

        self.assertEqual(
            records[1].subpath_index,
            1,
        )


class PathMetricTests(
    GeometryAssertions
):
    def make_polyline(self) -> Path:
        return Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        3.0,
                        4.0,
                    )
                ),
                LineTo(
                    Point(
                        9.0,
                        4.0,
                    )
                ),
            )
        )

    def test_path_length(self) -> None:
        path = self.make_polyline()

        self.assertFloatAlmostEqual(
            path.length(),
            11.0,
        )

    def test_path_bounds(self) -> None:
        path = self.make_polyline()

        self.assertEqual(
            path.bounds(),
            Bounds(
                0.0,
                0.0,
                9.0,
                4.0,
            ),
        )

    def test_point_at_length_first_segment(
        self,
    ) -> None:
        path = self.make_polyline()

        point = path.point_at_length(
            2.5
        )

        self.assertPointAlmostEqual(
            point,
            Point(
                1.5,
                2.0,
            ),
        )

    def test_point_at_length_second_segment(
        self,
    ) -> None:
        path = self.make_polyline()

        point = path.point_at_length(
            8.0
        )

        self.assertPointAlmostEqual(
            point,
            Point(
                6.0,
                4.0,
            ),
        )

    def test_point_at_length_clamps_negative(
        self,
    ) -> None:
        path = self.make_polyline()

        self.assertEqual(
            path.point_at_length(
                -100.0
            ),
            Point(
                0.0,
                0.0,
            ),
        )

    def test_point_at_length_clamps_overflow(
        self,
    ) -> None:
        path = self.make_polyline()

        self.assertEqual(
            path.point_at_length(
                1000.0
            ),
            Point(
                9.0,
                4.0,
            ),
        )

    def test_tangent_at_length(self) -> None:
        path = self.make_polyline()

        tangent = (
            path.tangent_at_length(
                8.0
            )
        )

        self.assertVectorAlmostEqual(
            tangent,
            Vector(
                1.0,
                0.0,
            ),
        )

    def test_subpath_lengths(self) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        3.0,
                        4.0,
                    )
                ),
                MoveTo(
                    Point(
                        100.0,
                        100.0,
                    )
                ),
                LineTo(
                    Point(
                        106.0,
                        100.0,
                    )
                ),
            )
        )

        lengths = (
            path.subpath_lengths()
        )

        self.assertEqual(
            len(lengths),
            2,
        )

        self.assertFloatAlmostEqual(
            lengths[0],
            5.0,
        )

        self.assertFloatAlmostEqual(
            lengths[1],
            6.0,
        )

    def test_empty_path_point_at_length_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            DegenerateGeometryError
        ):
            Path().point_at_length(
                0.0
            )


class PathNormalizationTests(
    GeometryAssertions
):
    def test_duplicate_close_is_removed(
        self,
    ) -> None:
        original = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        0.0,
                    )
                ),
                ClosePath(),
                ClosePath(),
            )
        )

        normalized = (
            original.normalized()
        )

        self.assertEqual(
            normalized.command_count,
            3,
        )

        self.assertIsInstance(
            normalized.commands[-1],
            ClosePath,
        )

    def test_repeated_empty_move_can_be_collapsed(
        self,
    ) -> None:
        original = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                MoveTo(
                    Point(
                        10.0,
                        10.0,
                    )
                ),
                LineTo(
                    Point(
                        20.0,
                        20.0,
                    )
                ),
            )
        )

        normalized = (
            original.normalized(
                preserve_empty_subpaths=False
            )
        )

        self.assertEqual(
            normalized.command_count,
            2,
        )

        self.assertEqual(
            normalized.commands[0],
            MoveTo(
                Point(
                    10.0,
                    10.0,
                )
            ),
        )


class PathTransformTests(
    GeometryAssertions
):
    def test_line_transform_exact(self) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        5.0,
                    )
                ),
            )
        )

        transform = (
            AffineTransform.translate(
                3.0,
                4.0,
            )
            @ AffineTransform.scale(
                2.0
            )
        )

        result = path.transformed(
            transform
        )

        self.assertIsInstance(
            result,
            PathTransformResult,
        )

        self.assertEqual(
            result.approximations,
            (),
        )

        self.assertEqual(
            result.path.commands[0],
            MoveTo(
                Point(
                    3.0,
                    4.0,
                )
            ),
        )

        self.assertEqual(
            result.path.commands[1],
            LineTo(
                Point(
                    23.0,
                    14.0,
                )
            ),
        )

    def test_bezier_transform_exact(
        self,
    ) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                CubicTo(
                    control1=Point(
                        0.0,
                        10.0,
                    ),
                    control2=Point(
                        20.0,
                        10.0,
                    ),
                    end=Point(
                        20.0,
                        0.0,
                    ),
                ),
            )
        )

        result = path.transformed(
            AffineTransform.scale(
                2.0,
                3.0,
            )
        )

        command = (
            result.path.commands[1]
        )

        self.assertIsInstance(
            command,
            CubicTo,
        )

        self.assertEqual(
            command.control1,
            Point(
                0.0,
                30.0,
            ),
        )

        self.assertEqual(
            command.control2,
            Point(
                40.0,
                30.0,
            ),
        )

        self.assertEqual(
            command.end,
            Point(
                40.0,
                0.0,
            ),
        )

    def test_arc_preserved_under_uniform_similarity(
        self,
    ) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        1.0,
                        0.0,
                    )
                ),
                ArcTo(
                    rx=1.0,
                    ry=2.0,
                    x_axis_rotation=15.0,
                    large_arc=False,
                    sweep=True,
                    end=Point(
                        0.0,
                        1.0,
                    ),
                ),
            )
        )

        transform = (
            AffineTransform.rotate(
                30.0
            )
            @ AffineTransform.scale(
                4.0
            )
        )

        result = path.transformed(
            transform
        )

        self.assertEqual(
            result.approximations,
            (),
        )

        command = (
            result.path.commands[1]
        )

        self.assertIsInstance(
            command,
            ArcTo,
        )

        self.assertFloatAlmostEqual(
            command.rx,
            4.0,
        )

        self.assertFloatAlmostEqual(
            command.ry,
            8.0,
        )

        self.assertFloatAlmostEqual(
            command.x_axis_rotation,
            45.0,
        )

    def test_arc_becomes_cubics_under_nonuniform_scale(
        self,
    ) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        1.0,
                        0.0,
                    )
                ),
                ArcTo(
                    rx=1.0,
                    ry=1.0,
                    x_axis_rotation=0.0,
                    large_arc=False,
                    sweep=True,
                    end=Point(
                        0.0,
                        1.0,
                    ),
                ),
            )
        )

        result = path.transformed(
            AffineTransform.scale(
                2.0,
                3.0,
            )
        )

        self.assertGreaterEqual(
            len(
                result.approximations
            ),
            1,
        )

        self.assertTrue(
            all(
                isinstance(
                    command,
                    (
                        MoveTo,
                        CubicTo,
                    ),
                )
                for command
                in result.path.commands
            )
        )

        approximation = (
            result.approximations[0]
        )

        self.assertIsInstance(
            approximation,
            ApproximationRecord,
        )

        self.assertEqual(
            approximation.operation,
            "affine-transform-arc-to-cubic",
        )

        self.assertGreaterEqual(
            approximation.generated_segment_count,
            1,
        )


class FlatteningTests(
    GeometryAssertions
):
    def test_line_flattening(self) -> None:
        segment = LineSegment(
            Point(
                0.0,
                0.0,
            ),
            Point(
                10.0,
                10.0,
            ),
        )

        points = flatten_segment(
            segment
        )

        self.assertEqual(
            points,
            (
                Point(
                    0.0,
                    0.0,
                ),
                Point(
                    10.0,
                    10.0,
                ),
            ),
        )

    def test_quadratic_flattening(
        self,
    ) -> None:
        segment = (
            QuadraticBezierSegment(
                Point(
                    0.0,
                    0.0,
                ),
                Point(
                    50.0,
                    100.0,
                ),
                Point(
                    100.0,
                    0.0,
                ),
            )
        )

        points = flatten_segment(
            segment,
            tolerance=1.0,
        )

        self.assertGreater(
            len(points),
            2,
        )

        self.assertEqual(
            points[0],
            segment.start,
        )

        self.assertEqual(
            points[-1],
            segment.end,
        )

    def test_cubic_flattening(self) -> None:
        segment = CubicBezierSegment(
            Point(
                0.0,
                0.0,
            ),
            Point(
                0.0,
                100.0,
            ),
            Point(
                100.0,
                100.0,
            ),
            Point(
                100.0,
                0.0,
            ),
        )

        points = flatten_segment(
            segment,
            tolerance=1.0,
        )

        self.assertGreater(
            len(points),
            2,
        )

    def test_arc_flattening(self) -> None:
        arc = EllipticalArcSegment(
            start=Point(
                1.0,
                0.0,
            ),
            rx=1.0,
            ry=1.0,
            x_axis_rotation=0.0,
            large_arc=False,
            sweep=True,
            end=Point(
                0.0,
                1.0,
            ),
        )

        points = flatten_segment(
            arc,
            tolerance=0.01,
        )

        self.assertGreater(
            len(points),
            2,
        )

        self.assertPointAlmostEqual(
            points[0],
            arc.start,
        )

        self.assertPointAlmostEqual(
            points[-1],
            arc.end,
        )

    def test_compound_path_flattening(
        self,
    ) -> None:
        path = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        0.0,
                    )
                ),
                ClosePath(),
                MoveTo(
                    Point(
                        20.0,
                        20.0,
                    )
                ),
                QuadraticTo(
                    control=Point(
                        30.0,
                        40.0,
                    ),
                    end=Point(
                        40.0,
                        20.0,
                    ),
                ),
            )
        )

        flattened = flatten_path(
            path,
            tolerance=0.5,
        )

        self.assertIsInstance(
            flattened,
            FlattenedPath,
        )

        self.assertEqual(
            len(
                flattened.subpaths
            ),
            2,
        )

        first = (
            flattened.subpaths[0]
        )

        second = (
            flattened.subpaths[1]
        )

        self.assertIsInstance(
            first,
            FlattenedSubpath,
        )

        self.assertTrue(
            first.closed
        )

        self.assertFalse(
            second.closed
        )

        self.assertGreaterEqual(
            len(first.points),
            2,
        )

        self.assertGreater(
            len(second.points),
            2,
        )


class StrokeBoundsTests(
    GeometryAssertions
):
    def test_round_join_expansion(self) -> None:
        base = Bounds(
            0.0,
            0.0,
            100.0,
            100.0,
        )

        result = stroke_aware_bounds(
            base,
            width=10.0,
            line_join=(
                StrokeLineJoin.ROUND
            ),
        )

        self.assertEqual(
            result,
            Bounds(
                -5.0,
                -5.0,
                105.0,
                105.0,
            ),
        )

    def test_bevel_join_expansion(self) -> None:
        base = Bounds(
            0.0,
            0.0,
            100.0,
            100.0,
        )

        result = stroke_aware_bounds(
            base,
            width=10.0,
            line_join=(
                StrokeLineJoin.BEVEL
            ),
        )

        self.assertEqual(
            result,
            Bounds(
                -5.0,
                -5.0,
                105.0,
                105.0,
            ),
        )

    def test_miter_conservative_expansion(
        self,
    ) -> None:
        base = Bounds(
            0.0,
            0.0,
            100.0,
            100.0,
        )

        result = stroke_aware_bounds(
            base,
            width=10.0,
            line_join=(
                StrokeLineJoin.MITER
            ),
            miter_limit=4.0,
        )

        self.assertEqual(
            result,
            Bounds(
                -20.0,
                -20.0,
                120.0,
                120.0,
            ),
        )


class NativeBackendTests(
    GeometryAssertions
):
    def test_backend_identity(self) -> None:
        backend = (
            NATIVE_GEOMETRY_BACKEND
        )

        self.assertIsInstance(
            backend,
            NativeGeometryBackend,
        )

        self.assertIsInstance(
            backend,
            GeometryBackend,
        )

        self.assertEqual(
            backend.backend_id,
            "savant-native-geometry",
        )

        self.assertEqual(
            backend.backend_version,
            MODULE_VERSION,
        )

    def make_paths(
        self,
    ) -> tuple[Path, Path]:
        left = Path(
            commands=(
                MoveTo(
                    Point(
                        0.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        0.0,
                    )
                ),
                LineTo(
                    Point(
                        10.0,
                        10.0,
                    )
                ),
                ClosePath(),
            )
        )

        right = Path(
            commands=(
                MoveTo(
                    Point(
                        5.0,
                        5.0,
                    )
                ),
                LineTo(
                    Point(
                        15.0,
                        5.0,
                    )
                ),
                LineTo(
                    Point(
                        15.0,
                        15.0,
                    )
                ),
                ClosePath(),
            )
        )

        return (
            left,
            right,
        )

    def test_boolean_explicitly_unsupported(
        self,
    ) -> None:
        left, right = (
            self.make_paths()
        )

        for operation in (
            BooleanOperation.UNION,
            BooleanOperation.INTERSECTION,
            BooleanOperation.DIFFERENCE,
            BooleanOperation.XOR,
        ):
            with self.subTest(
                operation=operation.value
            ):
                with self.assertRaises(
                    UnsupportedFeatureError
                ):
                    NATIVE_GEOMETRY_BACKEND.boolean(
                        operation,
                        left,
                        right,
                    )

    def test_offset_explicitly_unsupported(
        self,
    ) -> None:
        left, _ = self.make_paths()

        with self.assertRaises(
            UnsupportedFeatureError
        ):
            NATIVE_GEOMETRY_BACKEND.offset(
                left,
                5.0,
            )

    def test_stroke_to_path_explicitly_unsupported(
        self,
    ) -> None:
        left, _ = self.make_paths()

        with self.assertRaises(
            UnsupportedFeatureError
        ):
            (
                NATIVE_GEOMETRY_BACKEND
                .stroke_to_path(
                    left,
                    width=10.0,
                    line_join=(
                        StrokeLineJoin.MITER
                    ),
                    line_cap=(
                        StrokeLineCap.BUTT
                    ),
                    miter_limit=4.0,
                )
            )


class IntegratedGeometryProofTests(
    GeometryAssertions
):
    def test_complex_geometry_pipeline(
        self,
    ) -> None:
        source = Path(
            commands=(
                MoveTo(
                    Point(
                        10.0,
                        20.0,
                    )
                ),
                LineTo(
                    Point(
                        80.0,
                        20.0,
                    )
                ),
                QuadraticTo(
                    control=Point(
                        120.0,
                        20.0,
                    ),
                    end=Point(
                        120.0,
                        60.0,
                    ),
                ),
                CubicTo(
                    control1=Point(
                        120.0,
                        120.0,
                    ),
                    control2=Point(
                        40.0,
                        140.0,
                    ),
                    end=Point(
                        20.0,
                        90.0,
                    ),
                ),
                ArcTo(
                    rx=35.0,
                    ry=20.0,
                    x_axis_rotation=30.0,
                    large_arc=False,
                    sweep=True,
                    end=Point(
                        10.0,
                        20.0,
                    ),
                ),
                ClosePath(),
            ),
            fill_rule=FillRule.NONZERO,
        )

        source_bounds = (
            source.bounds()
        )

        self.assertIsNotNone(
            source_bounds
        )

        self.assertGreater(
            source.length(),
            0.0,
        )

        midpoint = (
            source.point_at_length(
                source.length()
                / 2.0
            )
        )

        self.assertPointInsideBounds(
            midpoint,
            source_bounds,
            epsilon=1.0e-6,
        )

        transform = (
            AffineTransform.translate(
                250.0,
                100.0,
            )
            @ AffineTransform.skew_x(
                12.0
            )
            @ AffineTransform.scale(
                1.5,
                0.75,
            )
        )

        transformed = (
            source.transformed(
                transform
            )
        )

        self.assertGreaterEqual(
            len(
                transformed.approximations
            ),
            1,
        )

        transformed_bounds = (
            transformed.path.bounds()
        )

        self.assertIsNotNone(
            transformed_bounds
        )

        flattened = flatten_path(
            transformed.path,
            tolerance=0.25,
        )

        self.assertEqual(
            len(
                flattened.subpaths
            ),
            1,
        )

        self.assertGreater(
            len(
                flattened.subpaths[0].points
            ),
            5,
        )

        conservative = (
            stroke_aware_bounds(
                transformed_bounds,
                width=8.0,
                line_join=(
                    StrokeLineJoin.MITER
                ),
                miter_limit=4.0,
            )
        )

        self.assertLessEqual(
            conservative.min_x,
            transformed_bounds.min_x,
        )

        self.assertLessEqual(
            conservative.min_y,
            transformed_bounds.min_y,
        )

        self.assertGreaterEqual(
            conservative.max_x,
            transformed_bounds.max_x,
        )

        self.assertGreaterEqual(
            conservative.max_y,
            transformed_bounds.max_y,
        )


def main() -> int:
    print(
        "SAVANT Filament Vector Renderer"
    )

    print(
        "geometry.py comprehensive self-test"
    )

    print(
        f"module version: {MODULE_VERSION}"
    )

    print(
        f"geometry schema: {GEOMETRY_SCHEMA}"
    )

    print()

    suite = (
        unittest.defaultTestLoader
        .loadTestsFromModule(
            __import__(
                __name__
            )
        )
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
            "ALL GEOMETRY.PY PROOFS PASSED"
        )

        return 0

    print(
        "GEOMETRY.PY PROOF FAILURE"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
