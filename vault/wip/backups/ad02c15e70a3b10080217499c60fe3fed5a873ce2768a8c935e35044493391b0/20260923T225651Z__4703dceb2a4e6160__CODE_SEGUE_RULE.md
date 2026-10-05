# CODE SEGUE RULE

STATUS: CANON
AUTHORITY: USER DIRECTIVE
ACCEPTED: 2026-09-23
DEPENDS_ON: AD-20260923-001
PRESERVES: AD-20260813-006

## Core rule

Programming composition is Segue-mediated wherever a transition possesses independently meaningful semantics.

Code units do not require artificial direct coupling when the relationship between them can be represented explicitly.

## Canonical edifice transitions

```text
glyph → line
line → segment
segment → snippet
snippet → script
script → engine
engine → subsystem
subsystem → system
system → application
```

## Additional valid endpoints

A code Segue may also connect independently meaningful functional structures such as:

- line → line;
- segment → segment;
- snippet → snippet;
- script → script;
- engine → engine;
- subsystem → subsystem;
- system → system;
- function → function;
- method → method;
- callable → callable;
- block → block;
- adapter → contract;
- provider → adapter;
- command → runtime;
- validator → subject;
- test → subject.

These structures do not thereby become programming-edifice levels.

## Segue responsibilities

A code Segue may encode:

- control transfer;
- data transfer;
- type conversion;
- contract adaptation;
- lifecycle transition;
- error transition;
- state transition;
- dependency boundary;
- compatibility boundary;
- normalization;
- serialization;
- deserialization;
- validation handoff;
- provider handoff;
- projection handoff;
- composition attachment.

## Segue identity

A stable reusable Segue exposes, where applicable:

- id;
- source;
- target;
- type;
- authority;
- lineage;
- provenance;
- dependencies;
- compatibility;
- contract;
- validation;
- extensions.

## Non-duplication law

A Segue references its endpoints.
It does not duplicate them.
Reusable transition behavior is substantiated once and instanced wherever compatible.

## Granularity law

Not every adjacency requires a materialized Segue.

A Segue becomes a stable instance when the transition itself requires identity, reuse, policy, validation, compatibility, observation, extension, or governance.

Pure language syntax remains syntax.

Savant must not create meaningless Segue objects between every glyph or source line merely to satisfy structural aesthetics.

## Projection

Projected code may render Segue behavior as ordinary native source syntax.

The absence of a visible `segue` keyword in generated source does not erase an underlying governed composition relationship.

Generated source remains a projection of the composition graph where that graph is authoritative.
