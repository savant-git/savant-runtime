# Architecture Before Modernization

## System shape

The repository is a filesystem-oriented Python and shell system with two principal, weakly integrated planes:

1. `canon-system/` treats YAML below `authority/` as authoritative. `runtime/canonctl.py` validates records against JSON Schema, renders Markdown projections and a manifest, and rebuilds a derived SQLite database. `canon_proposals.py` manages a separate proposal workflow that ultimately invokes the same projection pipeline.
2. `runtime/palaver/` and `tools/` scan filesystem state and compile derived graph, field, topology, authority, lineage, ownership, and refactoring artifacts into `vault/` and `authority_graph/`. Most are standalone scripts with hard-coded roots and import-time effects rather than reusable packages.

`palaver_voice_backend.py` is a standalone Flask HTTP bridge to external AI providers and an Envoy voice implementation expected through the externally linked ontology tree. Root-level shell scripts form a chronological collection of builders, repairs, installers, reports, and deployment patches. There is no single canonical build/deploy interface.

## Runtime and data flow

- Canon: authority YAML -> schema validation -> generated Markdown/manifest -> generated SQLite.
- Filesystem observatory: selected directories -> heuristic scan -> generated JSON graphs/indexes in `vault/`.
- Conversation: browser/Vite (external symlink dependency) -> Flask on loopback port 8787 -> Gemini or OpenAI -> optional Envoy voice runtime.
- Operations: root-level scripts generate or modify files, processes, systemd units, packages, tunnels, and runtime state.

## Baseline boundaries and risks

- The checked-out copy is not self-contained: eleven tracked symlinks exist, most targeting `/root/savant-runtime`; repository-relative UI/Palaver links transitively depend on the external ontology link.
- 125 tracked files reference `/root/savant-runtime`. Running many scripts from this copy would read or mutate the immutable reference repository.
- A tracked service environment file contained plaintext credential assignments. Values were not reproduced; current-tree removal and credential rotation are required.
- Canon projections are reproducible, but database rebuild and supersession mutate live files non-atomically.
- Palaver runtime modules frequently scan/write at import time and lack shared configuration or stable package APIs.
- The backend loads external environment files implicitly, uses unrestricted CORS, accepts unbounded unauthenticated requests, leaks exception details, and can fail offline due to an uninitialized variable.
- There were no tests, CI workflows, packaging metadata, lockfiles, lint/type/format configuration, container definitions, or canonical systemd unit sources.

## Baseline validation

- All 104 tracked shell scripts parse with `bash -n`.
- All 30 tracked Python files parse as AST; all tracked JSON parses.
- Canon validation passes for 31 records.
- Isolated projection and database regeneration passes; projections match and SQLite output is byte-identical.
- The existing SQLite database passed integrity validation through Python's `sqlite3` module during specialist review.
- Live services, external APIs, host package operations, systemd changes, and external symlink targets were intentionally not exercised.
