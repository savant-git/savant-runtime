# Diagnostics Report

`ConstitutionalPlatform` emits diagnostics for rejected projections and dependency failures. Every `Diagnostic` contains its object identity, stable code, message, optional failed dependency, plus authority, lineage, and provenance chains resolved by the existing constitutional registry.

`health()` projects healthy, degraded, invalid, deprecated, or failed states without persisting health. Current automatic evaluation maps successful validation to healthy, failed validation to invalid, and deprecated/retired lifecycle to deprecated. Additional states are available to subsystem diagnostics without creating authoritative fields.

Metrics record bootstrap, discovery, validation, projection, and dependency traversal duration together with registry and graph size. Bus topics cover lifecycle, projection, projection rejection, and diagnostics; subsystem lifecycle calls cover registration and validation coordination. Bus events are in-memory notifications and are not constitutional events or authoritative state.

Phase 6 tests verify diagnostic traceability, rejected-projection explanations, health projection, metrics, and bus delivery.

