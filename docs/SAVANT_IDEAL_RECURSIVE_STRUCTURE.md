# Savant Ideal Recursive Structure

Status: proposed architecture  
Authority: current project-owner directive  
Migration status: not authorized  
Primary objective: preserve Savant’s existing hierarchy while making ownership, composition, moods, instances, utilities, programs, tasks, runtime state, and projections deterministic.

---

# 1. Core conclusion

Savant requires three coordinated structures.

## 1.1 Containment structure

Containment answers:

> Where does this element canonically belong?

It is represented by the properly nested hierarchy and filesystem.

Examples:

- obelisks contain gates through the accepted hierarchy;
- gates contain innates through their segue;
- innates contain exiles through their segue;
- exiles contain prodigals through their segue;
- prodigals contain quirks through their segue;
- programs belong inside the element that owns them;
- utilities shared by several sibling elements belong at their narrowest shared scope.

Containment is declared once.

Children, ancestry, descendants, and views are projected.

## 1.2 Composition structure

Composition answers:

> What instances constitute this element?

It is represented by an authoritative instance graph.

An element does not need physical copies of everything it uses.

It references canonical instances.

## 1.3 Transformation structure

Transformation answers:

> What does this element do under a mood, or when two moods combine?

It is represented by mood applications and mood-combination records.

Moods do not determine containment.

Moods do not determine file ownership.

Moods alter behavior, projection, assembly, interpretation, or execution.

These three structures must never be collapsed into one directory tree.

---

# 2. Filesystem responsibility

The filesystem is responsible for nine things:

1. canonical element placement;
2. canonical program placement;
3. canonical reusable utility placement;
4. canonical authority placement;
5. source and test locality;
6. schema and contract locality;
7. runtime-state separation;
8. report and history separation;
9. human navigation.

The filesystem is not responsible for physically expressing every composition, relationship, attachment, mood, slot, descendant view, or task roll-up.

Those are graph records and projections.

---

# 3. Governing placement rule

Every artifact is placed according to this decision order:

1. determine whether it is authority, source, runtime state, history, evidence, report, cache, or projection;
2. determine whether it implements one program or is reusable;
3. determine the element that owns its meaning;
4. determine the narrowest scope containing all legitimate consumers;
5. preserve the accepted hierarchy nesting;
6. distinguish canonical substance from generated views;
7. distinguish instance identity from instance use;
8. distinguish mood definition from mood application;
9. assign one canonical path.

Pseudo-rule:

```text
canonical_path =
    place(
        artifact_kind,
        semantic_owner,
        program_owner,
        narrowest_shared_scope,
        authority_state
    )
