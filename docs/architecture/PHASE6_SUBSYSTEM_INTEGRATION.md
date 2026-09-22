# Subsystem Integration Report

## Audit result

Before Phase 6, no module outside `runtime/constitution` imported the constitutional substrate. Existing lineage, kinship, envoy, and Palaver implementations therefore remained behaviorally independent. Their domain-specific graphs and registries were not replaced because they encode runtime behavior, while `runtime/constitution/graph.py` and `registry.py` encode constitutional metadata.

Each executable service now exposes exactly one thin `constitutional.py` entry point:

- `runtime/envoy/constitutional.py`
- `runtime/kinship/constitutional.py`
- `runtime/lineage/constitutional.py`
- `runtime/palaver/authority/constitutional.py`
- `runtime/palaver/graph/constitutional.py`
- `runtime/palaver/investigation/constitutional.py`
- `runtime/palaver/search/constitutional.py`
- `runtime/palaver/topology/constitutional.py`

`ConstitutionalPlatform.discover_subsystems()` discovers these files recursively; there is no registration table or service switch. Each entry point references the pre-existing service identity and implementation module, preserving runtime APIs and execution semantics.

## Compatibility

All 24 lineage tests pass. The kinship no-regression validator confirms its pre-existing baseline (2 passing, 4 known recursion errors) is unchanged. Platformization did not modify lineage, kinship, envoy, or Palaver execution code.

