# Constitutional migration

## Compatibility contract

This is a zero-behavior migration. `runtime.constitution` is read-only and opt-in. Existing imports, command lines, authority files, lineage roles, kinship planes, services, and runtime paths are unchanged.

## Adding a future subsystem

1. Add only its direct authoritative assertion to `canon-system/authority/constitution/catalog.json`, or retain an existing authority source and add an adapter as done for Exiles.
2. Give it a stable graph ID, authority, provenance, `created_from`, dependencies, direct relationships, and implementation references.
3. Attach it to one constitutional domain with `parent`.
4. For a Service, declare one Faculty owner and its implementing Exile dimensions. Add System dependencies only where constrained by existing authority.
5. Do not write children, ancestry, inverse edges, Faculty × System rows, graphs, diagrams, or target views. They are compiler output.
6. Run `scripts/validate_constitution.sh`.

## Projection API

```python
from runtime.constitution import ConstitutionalRegistry

constitution = ConstitutionalRegistry.load()
runtime_view = constitution.project("runtime")
graph_view = constitution.graph()
object_view = constitution.object("service:lineage")
```

CLI targets are `documentation`, `implementation`, `graph`, `visualization`, `runtime`, `future_tooling`, and `faculty-system-matrix`:

```bash
python3 -m runtime.constitution.cli graph
```

Projection output is disposable and must not be checked in as authority.

## Rollback

Because no existing behavior imports the layer, rollback consists only of removing `runtime/constitution`, its catalog, tests, validator, and these documents. No data or executable migration is required.

## Existing validation baseline

At integration time all 24 existing lineage tests pass. Four of six pre-existing kinship tests fail with unbounded recursion in `runtime/kinship/algebra.py`; the constitutional package does not import or alter kinship and its tests reproduce the same failure in a separate process. The validator intentionally preserves that non-zero result rather than masking an inherited defect.
