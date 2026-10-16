# Lifecycle Report

`LifecyclePhase` defines: declared, discovered, validated, registered, bootstrapped, ready, projected, active, deprecated, and retired.

`LifecycleTracker.transition()` accepts only edges in `_TRANSITIONS`. The normal bootstrap path is linear through ready; projection advances ready or active objects through projected to active. Active objects may be projected again or deprecated; deprecated objects may only retire; retired objects have no outgoing transition.

State is not added to `ConstitutionalObject` and is never serialized as authoritative data. Lifecycle notifications travel through `ConstitutionalBus` and therefore remain transport evidence only.

`test_lifecycle_is_deterministic_and_illegal_transitions_fail` verifies the complete start path and deterministic rejection of an illegal transition.

