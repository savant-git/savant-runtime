# Phase 4 performance report

Measured on 2026-07-21 in the delivery container.

| Operation | Median |
|---|---:|
| Bootstrap | 349.649 ms |
| Runtime discovery | 179.687 ms |
| Complete migration | 287.037 ms |
| Registry lookup (1,000 samples) | <0.001 ms |
| Graph traversal | 0.021 ms |
| JSON projection | 49.324 ms |
| Complete migration validation | 1,485.736 ms |

Validation intentionally performs each required projection twice to prove determinism. That dominates the profile, while registry and traversal costs are negligible. Caching was not introduced because it would risk stale projected state and duplicate storage; no measured correctness-preserving optimization was warranted.
