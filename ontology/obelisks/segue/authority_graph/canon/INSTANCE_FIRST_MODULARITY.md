# INSTANCE-FIRST MODULARITY

STATUS: CANON
AUTHORITY: USER DIRECTIVE
DOMAIN: SAVANT RUNTIME
SCOPE: GLOBAL

## Core Rule

Everything that can be instanced must be instanced.

Files are not primary architecture.

Files are projections.

Primary primitives are:

- instances
- segues
- policies
- templates
- archetypes
- meta archetypes

## Required Properties

Every Savant artifact must expose:

- id
- kind
- version
- status
- authority
- lineage
- provenance
- dependencies
- relationships
- segues
- capabilities
- projections
- extensions
- future_extensions

## Modularity Rule

No subsystem may be a one-off.

No file may become a dead end.

No runtime component may require replacement to extend.

All functionality must be composable.

All functionality must support future attachment.

## Projection Rule

Generated files must expose what built them.

Every generated artifact must identify:

- source instances
- source templates
- source archetypes
- source segues
- source policies
- projection target

## Acceptance Gate

A Savant artifact is incomplete unless it can answer:

- What am I?
- What built me?
- What do I depend on?
- What depends on me?
- What do I project?
- What can attach to me later?
