# Outstanding Risks Report

## Concrete risks

1. Kinship recursion: `runtime/kinship/algebra.py:1138` recursively calls `determine()` without terminating for four existing functional cases. The dedicated `tests/constitution/validate_no_regression.py kinship` validator identifies 2 passing tests and these 4 errors as the preserved baseline. This blocks a literal all-repository-tests-green claim but is outside platformization and was not changed.
2. Validation cost: `ConstitutionalPlatform.start()` in `runtime/constitution/platform.py` retains bootstrap validation and then executes `ConstitutionalValidator` and `RuntimeMigrationValidator`. The measured platform median is 4.946 s, with migration validation at 2.342 s.
3. Integration boundary: subsystem entry points attach existing behavior to the substrate, but existing implementations such as `runtime/kinship/graph.py`, `runtime/lineage/registry.py`, and Palaver graph code still retain behavior-specific internal models. They must not be mistaken for constitutional authority; removal would change behavior and was not justified.
4. Commit unavailable: the supplied `/root/savant-runtime` tree contains no `.git` metadata, so no repository commit can be created without fabricating history.

## Recommendation

Address the kinship termination defect in a separately scoped behavior-preserving fix. Profile `RuntimeMigrationValidator.validate()` before considering cached validation. Keep subsystem-specific models strictly behind the one constitutional entry point and reject any future module that adds a second identity, authority, lineage, provenance, dependency, relationship, or projection authority.

