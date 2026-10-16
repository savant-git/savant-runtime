# Performance Report

Measured on 2026-07-21 after consolidation.

| Operation | Authority registry | Migrated registry |
|---|---:|---:|
| Bootstrap | 118.383 ms | 535.667 ms |
| Runtime discovery/migration | — | 281.526 / 417.438 ms |
| Registry lookup | <0.001 ms | <0.001 ms |
| Graph traversal | 0.033 ms | 0.022 ms |
| JSON projection | 28.952 ms | 54.754 ms |
| Validation | 995.252 ms | 2,095.103 ms |
| 5,000-node deep graph | 36.710 ms | — |
| 20,000-object kind lookup | 2.027 ms | — |

Validation is the measured bottleneck because every discovered target is projected twice to prove determinism. Runtime discovery is dominated by reading and parsing 57 files. Registry lookup and traversal are negligible. No cache was added: persisted or stale projection caches would conflict with the disposable projection rule, and no correctness-preserving optimization was demonstrated.
