# Constitutional field authority audit

The constitutional layer stores only the fifteen `ConstitutionalObject` primitives. Everything else is projected and disposable.

| Field | Class | Reason |
|---|---|---|
| `id` | AUTHORITATIVE | Immutable canonical identity. |
| `kind` | AUTHORITATIVE | Constitutional semantic classification. |
| `canonical_name` | AUTHORITATIVE | Stable constitutional name. |
| `display_name` | AUTHORITATIVE | Deliberately governed presentation label. |
| `description` | AUTHORITATIVE | Governed semantic statement. |
| `authority` | AUTHORITATIVE | Local authority declaration/override. |
| `status` | AUTHORITATIVE | Governed lifecycle declaration. |
| `version` | AUTHORITATIVE | Object revision version. |
| `created_at`, `updated_at` | AUTHORITATIVE | Revision evidence. |
| `lineage` | AUTHORITATIVE | Parent and supersession declarations. |
| `provenance` | AUTHORITATIVE | Source declarations. |
| `relationships` | AUTHORITATIVE | Explicit typed constitutional assertions. |
| `dependencies` | AUTHORITATIVE | Explicit dependency assertions. |
| `metadata` | AUTHORITATIVE | Extension declarations, aliases, and implementation references. |
| children, ancestors, descendants | PROJECTED | Rebuilt from `lineage.parent`. |
| canonical lookup, migrations | PROJECTED | Rebuilt from `id`, aliases, historical names, and supersession. |
| authority chain/effective authority | PROJECTED | Rebuilt by ordered inheritance and local overrides. |
| provenance/lineage chains | PROJECTED | Rebuilt through parent traversal. |
| graph nodes/edges/matrices | PROJECTED | Rebuilt from objects, relationships, dependencies, and lineage. |
| schema/validation results | PROJECTED | Rebuilt from discovered schemas and validators. |
| runtime/docs/Markdown/JSON/YAML/code/visualization | PROJECTED | Deterministic provider artifacts. |
| projection digest/source IDs/children | PROJECTED | Rebuilt from canonical projection inputs. |
| events | PROJECTED EVIDENCE | Append-only history, explicitly excluded from authoritative state. |

No projected value is written into the authority catalog.
