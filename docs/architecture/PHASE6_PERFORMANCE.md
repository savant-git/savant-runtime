# Performance Report

Measurements on 2026-07-21, milliseconds (median):

| Operation | Median |
|---|---:|
| Platform start | 4946.007 |
| Migration validation | 2342.071 |
| Migration bootstrap | 307.206 |
| Runtime migration | 283.742 |
| Discovery | 191.192 |
| Runtime projection | 53.103 |
| Deep recursion (5,000 nodes) | 23.167 |
| Large ontology query | 2.014 |
| Capability query | 0.617 |
| Graph traversal | 0.023 |
| Dependency traversal | 0.014 |
| Health projection | 0.005 |

Validation is the measured bottleneck. Platform start intentionally performs established constitutional bootstrap validation and then complete platform/migration validation; optimizing this safely requires shared immutable validation evidence or profiling within validators. No optimization was applied because that would change validation architecture without a demonstrated safe equivalence.

Registry lookup measured below timer resolution at this scale. No fixed recursion or ontology limit was observed in constitutional benchmarks.

