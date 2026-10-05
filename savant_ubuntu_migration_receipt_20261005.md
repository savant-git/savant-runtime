# savant ubuntu permanent migration receipt

date: 2026-10-05

status: complete

authority_effect: records accepted migration state; creates no duplicate runtime authority

## canonical runtime

canonical_host_role: ubuntu production host

canonical_runtime_root: /root/savant-runtime

canonical_writer: /root/savant-runtime on the ubuntu production host

writer_policy: single canonical writer

historical_source_policy: all pre-migration and non-canonical savant runtime copies are historical or recovery material only and are not authoritative writers unless explicitly promoted by later accepted authority.

## migration baseline

the permanent savant runtime has been migrated to the ubuntu production host at:

`/root/savant-runtime`

the migration preserves savant's existing authority hierarchy, lineage, provenance, runtime ownership boundaries, and deterministic projections.

## production persistence

palaver.service is enabled and active.

palaver-frontend.service is enabled and active.

palaver-attachment.service is enabled and active.

post-reboot verification established automatic production restart without manual runtime startup.

verified production listeners after reboot included:

- palaver frontend on port 5173
- palaver attachment service on localhost port 8791
- canonical palaver backend on localhost port 8787

## palaver production cutover

the palaver production cutover verifier completed successfully.

verified conditions included:

- canonical server launcher executable
- enterprise launcher executable
- production frontend build present
- production frontend runtime executable
- palaver.service enabled and active
- palaver-frontend.service enabled and active
- vite development server absent from production service
- production frontend runtime bound to service
- enterprise backend bootstrap valid
- backend health endpoint reachable
- frontend health endpoint reachable
- same-origin api projection valid
- frontend application root reachable
- compiled frontend asset reachable
- backend localhost-bound
- frontend production listener active

result:

`PALAVER PRODUCTION CUTOVER: valid`

the inactive palaver tunnel was informational and did not invalidate local production cutover.

## self-hosted migration gate

the current self-hosted migration gate completed successfully after reboot and again after the final palaver integration repair.

verified areas included:

- authoritative task graph
- fluid canon database
- opus router
- opus text inference surface
- envoy persona engine
- envoy voice engine
- envoy opus bridge
- envoy opus authority bridge
- envoy persona and voice integration
- palaver self-hosted development boundary
- palaver canonical server
- palaver envoy synthesis delegation
- palaver envoy persona default projection
- niche task governance runtime
- coda mutation runtime
- coda durable mutation surface
- notary evidence admission
- migration artifacts
- envoy segue entity
- envoy segue edges
- envoy segue lineage
- envoy segue contracts
- required json integrity

result:

`blocking_gap_count=0`

`migration_gate=ready`

`SAVANT SELF-HOSTED DEVELOPMENT CORE: READY`

## integrated inference

the canonical integrated inference path was verified after repairing standalone canonical package compatibility.

the canonical palaver bootstrap now installs the existing opus and envoy package compatibility machinery before loading the legacy palaver implementation.

this preserves the established compatibility architecture rather than duplicating or reimplementing opus or envoy behavior.

verified integrated execution:

`palaver -> scrybe -> fluid-canon -> envoy -> opus -> openai`

focused opus result:

`opus_result=success`

verified response:

`SAVANT_OPUS_OK`

scrybe live-context verification returned:

- ok: true
- canonical_memory_store: fluid-canon
- context_authoritative: false
- context_contains_token: true
- context_rebuildable: true
- independent_memory_store: false
- memory_attached: true
- opus_inference: true
- persistent_identity_present: false
- persistent_mutation: false
- production_formatter: true

verified trace:

`memory attached`
`openai ok`

the direct openai provider had independently been verified after reboot using the configured openai api credential, live provider endpoint, configured model resolution, and response extraction.

## runtime ownership

verified ownership boundaries remain:

- conversation: palaver
- provider execution: opus
- persona: envoy
- memory context: scrybe
- canonical memory store: fluid-canon
- mutation: coda
- task governance: niche

the migration does not transfer or duplicate those authorities.

## recovery

a whole-runtime recovery archive was created and validated.

archive object:

`s3://savant-ai-cluster/recovery/savant-runtime-full-20261005.tar.gz`

archive bytes:

`2139503978`

sha256:

`14b36da4c2fc9b0077b8ac7eef97f02f0ffca56f96ad1d5ab14da2bbdf59ffb7`

archive payload verification recorded:

- members: 155894
- regular file bytes: 22749755996
- gzip integrity: passed
- tar listing integrity: passed

the uploaded s3 object reported the expected object size and sha256 metadata.

streaming the remote s3 object back through sha256 verification produced the same digest:

`14b36da4c2fc9b0077b8ac7eef97f02f0ffca56f96ad1d5ab14da2bbdf59ffb7`

the temporary local recovery archive was subsequently removed after remote verification.

## restore-test status

an isolated full extraction and restore test was not performed.

reason:

the ubuntu root filesystem did not have sufficient safe free-space margin to hold the production runtime and a simultaneous full extracted recovery copy without adding storage.

the user explicitly directed migration to continue without adding space.

therefore:

- backup archive integrity is verified
- remote backup identity is verified
- remote backup readability is verified
- full isolated restore usability remains unproven

this deferred restore proof does not alter the verified production migration state, but it remains a recovery assurance limitation and must not be represented as passed.

## reboot proof

the ubuntu host was rebooted during migration verification.

after reboot:

- required palaver services returned automatically
- canonical listeners returned
- the self-hosted migration gate passed
- the palaver production cutover verifier passed
- direct provider execution succeeded
- integrated palaver, scrybe, envoy, opus, and openai execution succeeded

therefore production persistence across reboot is verified.

## single-writer cutover

effective with this receipt:

`/root/savant-runtime` on the ubuntu production host is the sole canonical savant runtime writer.

all earlier migration sources, workstation copies, mobile copies, staging copies, dumps, archives, snapshots, exported files, and recovery objects are non-authoritative historical or recovery material unless explicitly promoted by later accepted authority.

recovery artifacts may reproduce canonical state for recovery purposes but do not independently acquire writer authority.

no historical source may supersede current ubuntu state merely because it contains an older implementation, document, dump, or filesystem representation.

## deferred work that is not a migration blocker

the permanent ubuntu migration does not claim completion of unrelated savant product-development obligations.

unfinished product architecture, future native implementations, semantic work, storage-policy evolution, and other broader savant implementation tasks remain governed by their own authority and task state.

they do not invalidate this host migration.

## final state

permanent ubuntu migration: complete

canonical runtime: `/root/savant-runtime`

single canonical writer: established

self-hosted migration gate: ready

blocking migration gaps: 0

palaver production cutover: valid

reboot persistence: verified

integrated live inference: verified

remote whole-runtime backup: verified

isolated full restore test: deferred and explicitly unproven

historical migration sources: non-authoritative

savant may continue implementation from the ubuntu canonical runtime.
