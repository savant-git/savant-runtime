# Remaining Risks

Discovery in progress. External symlink targets, credential-dependent integrations, and live services will not be exercised without explicit safe local substitutes or authorization.

## Critical credential response required

The baseline commit contains a tracked plaintext service environment file with secret-like assignments. Its values were not copied into any audit artifact. The file is being removed from the current tree and replaced by a placeholder-only example, but every credential formerly stored there must be revoked or rotated outside this repository. The preserved baseline and Git object database still contain the historical file; history rewriting is intentionally not performed because it would violate baseline preservation and requires an explicitly coordinated incident-response decision.
