# SCRIPT COMPOSITION RULE

STATUS: CANON
AUTHORITY: USER DIRECTIVE
UPDATED: 2026-09-23
SUPERSESSION: AD-20260923-001
DEPENDS_ON: AD-20260813-006

Scripts are not atomic.

Canonical programming composition is:

```text
glyph
→ line
→ segment
→ snippet
→ script
→ engine
→ subsystem
→ system
→ application
```

A line is an ordered composition of glyph instances.
A segment is a bounded coherent composition of line instances.
A snippet is a reusable bounded composition of segment instances.
A script is an executable or interpretable composition of snippet instances and their typed Segues.
An engine composes script instances around one bounded operational mechanism.
A subsystem composes engine instances around one bounded internal capability domain.
A system composes subsystem instances around one independently coherent operational domain.
An application composes system instances into one operable application identity.

Every stable reusable programming level is instantiable.
Every higher level emerges through composition by reference rather than duplication.

Every script projection must expose, directly or transitively:

- source glyph instances;
- source line instances;
- source segment instances;
- source snippet instances;
- source Segues;
- assembled script identity;
- generated projection path;
- lineage;
- provenance;
- dependencies;
- dependents where known;
- future extension slots.

Files are projections unless explicitly authoritative.
The authoritative structure is the instance composition graph.
Transitions with independently meaningful semantics are represented through typed Segues.
No programming-edifice level requires a unique storage model.

The atomic programming-edifice level is `glyph`.
