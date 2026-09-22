# Modernization Plan

## Principles

Preserve authority YAML and public behavior where safe, make the repository root explicit and contained, turn derived outputs into reproducible artifacts, and add tests before or alongside behavior changes. Historical repair scripts will be classified and contained rather than cosmetically rewritten without evidence that they remain supported entry points.

## Prioritized phases

1. **P0 incident response and containment**: remove tracked credentials from the current tree, add safe examples/ignore rules, document rotation and historical exposure, prevent supported entry points from targeting the immutable reference, and avoid following external symlinks.
2. **P0 correctness and security**: make canon validation/writes and DB replacement safe; harden the Palaver API with explicit environment injection, authentication, request bounds, restrictive CORS, timeouts, generic errors, and deterministic offline behavior.
3. **P1 modularity and tests**: extract reusable configuration and pure functions, eliminate import-time work in supported modules, add unit/integration/API tests, and expose canonical commands from arbitrary working directories.
4. **P1 reproducibility and operations**: declare complete dependencies and supported runtime, add CI/static checks, provide canonical service/deployment templates with non-root sandboxing, and replace runtime package downloads.
5. **P2 historical lifecycle**: classify obsolete repair/build scripts and generated dumps, consolidate supported automation, archive or remove redundant artifacts when provenance is clear, and document regeneration/retention.
6. **Final review**: run the full available validation matrix, independent security/architecture/correctness/reliability/dependency reviews, remediate substantiated findings, and reconcile every inventory row.

## Dependencies and risks

- Credential revocation and Git-history remediation require external coordination; no secret value will be inspected or transmitted.
- External ontology/UI/voice sources are unavailable without leaving workspace boundaries, so integrations must degrade safely and remain explicitly unverified.
- Host-level service/package scripts cannot be executed safely in this environment; validate their syntax/templates and document controlled deployment instead.
- Broad root-path rewriting can change intended install semantics. Supported entry points will be corrected first; historical scripts require per-file classification.

## Rollback

All changes remain visible against baseline commit `1a85db3`. Each implementation phase will be kept coherent and validated. Generated canon outputs are regenerated only from authoritative YAML. No history rewrite, production database mutation, external service call, or host deployment is part of the modernization validation.
