# Savant Dry-Run Safety Engine

Status: executable, non-mutating.

The dry-run engine reconstructs an sdump projection into an isolated staging tree, simulates the proposed migration as compatibility-preserving copies, validates the staged tree, and emits one of three verdicts:

- `safe`: every modeled gate passes against a complete, hash-equivalent baseline;
- `unsafe`: a deterministic failure proves the change set must not be applied;
- `indeterminate`: no proven breakage was found, but evidence is incomplete or authority/compatibility remains unresolved.

The engine never modifies `/root/savant-runtime`.

## Canonical target

```text
/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/underscore/rubric/dry-run/
```

This placement remains proposed until live authority confirms the implementation owner.

## Absolute execution

```text
python3 /root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/underscore/rubric/dry-run/source/savant_dry_run.py \
  --dump /root/savant-runtime/sdump_savant-runtime_080526.txt \
  --proposal /root/savant-runtime/audit/structural-intelligence/20260805/migration-proposal.json \
  --output /root/savant-runtime/audit/dry-run/20260805
```

Exit codes:

```text
0 safe
2 indeterminate
3 unsafe
4 execution error
```

A `safe` result does not directly authorize mutation. Coda must still compare the live baseline digest, stage the accepted transaction, rerun the same gates, and obtain the required authority before commit.
