# Phase 3 benchmark and profile report

Measured on 2026-07-21 in the delivery container. Values are medians; the harness remains in `tests/constitution/benchmark_phase3.py`.

| Operation | Median |
|---|---:|
| Bootstrap | 70.758 ms |
| Registry lookup (1,000 samples) | <0.001 ms |
| Graph traversal | 0.034 ms |
| JSON projection | 13.715 ms |
| Full constitutional validation | 394.795 ms |
| 5,000-node deep traversal/build | 16.876 ms |
| 20,000-object kind lookup | 1.968 ms |

The cumulative profile attributes most time to defensive primitive thaw/copy work, repeated validation projections, and YAML serialization. These are correctness boundaries rather than algorithmic traversal bottlenecks. Lookup and traversal are already sub-millisecond, and no optimization was applied because caching disposable projections could introduce stale projected state or duplicate storage. Future optimization should begin with an explicitly scoped immutable snapshot cache and benchmark it against this baseline.
