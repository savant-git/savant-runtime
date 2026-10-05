# PROGRAMMING LEXICON CANON

STATUS: CANON
AUTHORITY: USER DIRECTIVE
ACCEPTED: 2026-09-23
DEPENDS_ON: AD-20260923-001
PRESERVES: AD-20260813-006

## Purpose

This document separates Savant's canonical programming edifice from orthogonal programming vocabulary required by implementation.

A term may be structurally important without being an edifice level.

## Canonical edifice terms

### glyph

The atomic Savant programming-edifice level and smallest canonical textual or symbolic source unit represented by the programming composition graph.

### line

Ordered composition of glyph instances forming one source line.

### segment

Bounded coherent composition of related line instances.

### snippet

Reusable bounded composition of one or more segment instances.

### script

Executable or interpretable composition of snippet instances and their Segues.

### engine

Bounded operational mechanism composed from script instances.

### subsystem

Bounded internal capability domain composed from engine instances.

### system

Independently coherent operational domain composed from subsystem instances.

### application

Operable application identity composed from system instances.

## Text and syntax terms

### character

Textual or encoding concept that may be used by languages, external specifications, compatibility surfaces, historical records, or ordinary textual descriptions.

`character` is not Savant's atomic programming-edifice level.

### token

Language-level lexical unit recognized by a parser or tokenizer.

### identifier

Token naming a language-level entity.

### literal

Source representation of a value.

### expression

Language construct evaluating to a value or result.

### statement

Language construct expressing an executable or declarative action.

### block

Language-defined grouping of statements or declarations.

These are syntax classifications, not Savant programming-edifice levels.

## Callable terms

### function

Named or addressable callable implementation.

### method

Callable bound through an object, class, or equivalent language construct.

### callable

General executable invocation surface.

### class

Language construct defining data and/or behavior according to the target language.

These may occur inside segments, snippets, scripts, or larger projections. Their native-language boundaries do not override Savant composition identity.

## Interface terms

### interface

Declared interaction surface.

### contract

Explicit requirements governing interaction between participants.

### schema

Machine-validatable structural contract for data or configuration.

### adapter

Compatibility mechanism translating one legitimate interface or representation into another.

### provider

Implementation supplying a bounded capability through a defined interface.

### validator

Mechanism evaluating a subject against explicit invariants or contracts.

These describe roles and boundaries rather than programming-edifice levels.

## Operational terms

### command

Invocable user, operator, or machine-facing execution entrypoint.

### test

Executable verification of behavior or invariants.

### migration

Governed transition from one compatible state or representation to another.

### task

Bounded unit of intended work.

### receipt

Evidence artifact recording execution, validation, mutation, or another governed event.

These are operational structures, not programming-edifice levels.

## Packaging terms

### file

Filesystem artifact.

A file may be a projection, evidence artifact, authority artifact, configuration, source representation, or another declared kind.

Filesystem presence alone establishes no authority.

### module

Language or packaging boundary grouping implementation.

Module remains valid terminology but is not a canonical Savant programming-edifice level.

### package

Packaging or namespace unit containing related implementation.

### library

Reusable implementation collection exposed for consumption.

### service

Operational deployment or interface boundary.

Service remains valid terminology but is not a canonical Savant programming-edifice level.

These do not compete with:

```text
glyph → line → segment → snippet → script → engine → subsystem → system → application
```

## Savant composition terms

### instance

Stable realization of a reusable semantic element.

### Segue

Typed relationship or transition connecting independently meaningful elements.

### Rubric

Executable implementation set owned by exactly one legitimate Savant element.

### Cabal

Genuinely shared implementation held at the narrowest legitimate common scope.

### projection

Reproducible representation derived from authoritative primitives.

### attachment

Extensible capability or relationship bound without replacing the subject.

### specialization

Compatible narrowing or extension of an existing canonical implementation.

### parameterization

Variation through explicit parameters rather than copied implementation.

## Classification law

One object may possess multiple orthogonal classifications.

For example, one projected Python file may simultaneously be:

- filesystem kind: file;
- language packaging kind: module;
- Savant projection kind: script projection;
- implementation owner: Rubric;
- edifice identity: script;
- composed from: snippets;
- containing native syntax: classes and functions.

These classifications do not conflict because they describe different axes.

## Anti-duplication law

New terminology must not be created merely to rename an existing concept.

New programming-edifice levels require explicit user authority.

Implementation roles must not silently become edifice levels through repeated filesystem use.

Historical terminology remains historical evidence unless current authority adopts it.

The atomic programming-edifice level is `glyph`.
