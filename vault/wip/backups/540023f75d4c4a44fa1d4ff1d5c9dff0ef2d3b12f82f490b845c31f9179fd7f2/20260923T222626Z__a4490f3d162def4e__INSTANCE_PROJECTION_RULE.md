# INSTANCE PROJECTION RULE

STATUS: CANON
AUTHORITY: USER DIRECTIVE
UPDATED: 2026-09-23
SUPERSESSION: AD-20260923-001
DEPENDS_ON: AD-20260813-006

Instances are authoritative only where their governing authority declares them authoritative.

Files are projections unless explicitly marked as authority.

Canonical programming projection follows:

```text
glyph instances
→ line instances
→ segment instances
→ snippet instances
→ script instances
→ engine instances
→ subsystem instances
→ system instances
→ application instances
```

Each higher programming-edifice level composes lower-level instances by reference.

A line instance composes ordered glyph instances.
A segment instance composes ordered line instances.
A snippet instance composes ordered segment instances.
A script instance composes ordered snippet instances and typed Segues.
An engine instance composes script instances.
A subsystem instance composes engine instances.
A system instance composes subsystem instances.
An application instance composes system instances.

A projection must preserve enough information to identify:

- projection id;
- source instance id;
- source child instances;
- source Segues;
- source policies;
- authority state;
- lineage;
- provenance;
- dependencies;
- generated path;
- compatibility;
- future extension slots.

Projected artifacts may be deleted and regenerated.
Deleting a projection must never delete its authoritative source instances.
Canonical substance must not be reconstructed from a projection when authoritative primitives remain available.
Instance chains may be superseded only through governing authority.

The atomic programming-edifice level is `glyph`.
