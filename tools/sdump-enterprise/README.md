# sdump enterprise v3

`sdump` creates a deterministic projection of authoritative source and canon.

Default behavior:

- uses the `compact` profile;
- excludes generated projections, archives, exports, audit bundles, caches, dependencies, binary assets, previous dumps, and secrets;
- stores repeated content once and records aliases through `duplicate_of`;
- records source SHA-256 and rendered SHA-256 separately;
- redacts common credentials while preserving source hashes;
- writes atomically under `savant-runtime/source`;
- uploads to S3 with SHA-256 metadata;
- verifies remote size and SHA-256 metadata;
- deletes the local artifact only after verification;
- leaves a receipt under `vault/sdump-receipts`.

Commands:

    sdump .
    sdump plan .
    sdump dump . --profile compact --no-upload
    sdump dump . --profile forensic --no-delete-after-upload
    sdump profiles
    sdump self-test
