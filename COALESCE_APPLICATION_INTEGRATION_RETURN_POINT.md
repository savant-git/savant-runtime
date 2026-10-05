This established that the server/projection boundary was reachable at that point in development.
It does not establish that every UI behavior was correct.
9. VERIFIED HISTORICAL PROJECTION
A Filament × Coalesce test eventually produced:
{'source': 'prodigal:modus:coalesce', 'piece_count': 72, 'record_count': 1, 'executed_piece_count': 72}
This established that the historical composition path could execute against one neutral record.
The 72-piece result belongs to the historical implementation.
It is not a future architectural requirement.
10. HISTORICAL INTEGRATION FAILURES
Failures encountered during development included missing Python modules:
projectors.docs_view
then:
projectors.base
then:
projectors.graph_view
These failures were encountered and subsequently progressed beyond during debugging.
Do not recreate fixes from memory.
Read the current Filament projector implementation before changing it.
11. HISTORICAL UI SERVER
The Coalesce UI was served historically at:
127.0.0.1:8789
Historical API path:
/api/coalesce/project
Historical health path:
/api/health
These are implementation observations, not permanent constitutional assignments.
12. HISTORICAL MOBILE ACCESS
The working Termux tunnel used:
ssh -N -L 8789:127.0.0.1:8789 root@108.175.4.80
The earlier address:
175.108.4.80
was incorrect for that successful connection.
Do not infer that 108.175.4.80 remains the current server address indefinitely.
13. HISTORICAL UI STATE
The Coalesce browser UI successfully loaded.
The interface exposed recipe selection and other controls.
At one stage, recipe selections could be changed in the dropdown but did not visibly produce corresponding application changes.
Therefore:
UI visibility is not proof that recipe projection is complete.
Future verification must check actual behavior rather than merely successful page rendering.
14. CURRENT UI CAPABILITY EVIDENCE
The historical coalesce.js implementation contained functionality for:
neutral dataset loading;
record normalization;
search;
relevance scoring;
kind filtering;
status filtering;
recipe selection;
grouping;
cards;
detail expansion;
selected-record state;
intel display;
bookmarks;
local bookmark persistence;
detail drawer;
density control;
keyboard search;
keyboard escape;
export;
JSON dataset import.
These behaviors are implementation evidence and candidates for reuse.
15. NEUTRAL DATA MODEL
Historical normalization accepted heterogeneous records and projected fields including:
id
date
title
preview
body
kind
status
category
provenance
relationships
This neutral data model should be preserved unless stronger current authority supersedes it.
Source-specific schemas should preferably enter through adapters.
16. APPLICATION RECIPE EVIDENCE
Historical UI recipe identities included:
chronology-explorer
evidence-atlas
dependency-browser
decision-history
system-health
authority-explorer
masterplan-viewer
provenance-explorer
narrative-atlas
Do not assume these names alone mean nine completely different applications.
Some may be projections/configurations of shared capabilities.
17. CURRENT EXTRACTION GOAL
The newly supplied source application should become another demonstration that Coalesce can construct useful applications from reusable components.
The goal is not merely visual reproduction.
Success requires demonstrating that the application's functional grammar can be expressed through reusable Coalesce composition.
18. COMPONENT REUSE ORDER
For every source capability, evaluate reuse in this order:
authoritative existing Savant primitive;
existing appropriate Prodigal;
existing appropriate Quirk;
existing Coalesce-native primitive;
configuration of an existing primitive;
adapter;
provider;
projection;
genuinely new generic primitive.
Do not skip directly to number nine.
19. EXILE RULE DURING CURRENT WORK
Do not embed Exiles into the new Coalesce application.
If the application needs an Exile-owned capability, keep that capability outside the composition boundary.
Use an authorized interface if one exists.
Do not copy Exile implementation into Coalesce.
20. INSTANCE RULE
When using reusable Savant elements, prefer instances/references.
An application-specific configuration should point back to the canonical source identity.
Do not fork the canonical implementation merely because the application requires different parameters.
21. APPLICATION CONFIGURATION
Application-specific differences should preferably live in:
recipe;
parameters;
instance configuration;
typed relationships;
projection configuration;
optional capability bindings.
Application-specific differences should not proliferate nearly identical primitives.
22. CURRENT VALIDATION BUDGET
For the current integration task, validation should remain bounded.
Required:
syntax/compilation;
one focused functional application test;
one relevant Filament/UI/API integration check.
Do not create a large new testing system solely for this integration.
23. FOCUSED FUNCTIONAL TEST
The representative test should use neutral data.
It should prove at minimum:
the application recipe resolves;
composition executes;
a neutral record enters the system;
the expected application projection is produced;
no source-domain data is required.
24. INTEGRATION CHECK
The integration check should prove the application can travel through the intended current projection path.
Where Filament remains the verified projection path, verify Filament.
Where the browser server remains relevant, verify its health endpoint and one real projection.
Do not treat HTTP 200 alone as proof that application behavior works.
25. DO NOT REBUILD COALESCE DURING THIS TASK
Do not:
replace the 81-piece registry;
implement the complete 27-piece migration;
reorganize all historical service families;
redesign every recipe;
remove compatibility behavior;
perform broad Coalesce architectural cleanup.
Those belong to the later bounded Coalesce migration.
26. ALLOWED CURRENT CHANGES
Current changes may include:
source application extraction;
a required generic adapter;
a required missing reusable primitive;
a required recipe;
a required projection;
a required compatibility fix;
a required integration repair.
Every change must be necessary to make the current application work.
27. CURRENT STOPPING CONDITION
Stop the current integration task when:
the source application's useful generic behavior has been extracted;
source-domain data has been removed from generic Coalesce substance;
the application is represented compositionally;
required existing Savant components are reused;
the application executes against neutral data;
the projection works;
syntax/compilation passes;
one focused functional test passes;
one integration check passes;
no known blocker prevents use.
Then stop.
Do not begin the 27-piece migration automatically.
28. NEXT TASK AFTER CURRENT COMPLETION
After the current application integration is complete:
Return to:
/root/savant-runtime/COALESCE_ARCHITECTURE_CANON.md
Then begin a new bounded task:
Coalesce 81-to-27 architectural migration.
That task begins by reading the verified implementation and creating the semantic mapping.
It does not begin by deleting pieces.
29. RECORDKEEPING RULE GOING FORWARD
Every substantial Savant concept or deferred implementation should receive a detailed return-point Markdown record.
A useful return-point record should preserve:
identity;
purpose;
owner;
architectural placement;
accepted decisions;
verified implementation state;
relevant paths;
dependencies;
dependents;
invariants;
known failures;
unresolved questions;
future work;
validation requirements;
completion condition;
explicit things not to do.
The record should be sufficient to resume the work without depending on conversational memory.
30. AUTHORITY DISCIPLINE FOR RETURN-POINT FILES
A return-point Markdown file is not automatically constitutional canon.
Its authority status must be stated explicitly.
Use categories such as:
ACCEPTED DESIGN AUTHORITY
ACTIVE WORK RECORD
VERIFIED IMPLEMENTATION RECORD
HISTORICAL RECORD
PROPOSAL
UNRESOLVED DESIGN
Do not silently convert notes into authority merely by placing them on disk.
31. FINAL RETURN POINT
Resume from this exact principle:
Finish the current application using the verified Coalesce baseline. Preserve what is learned from that integration. Then rebuild Coalesce itself as a separate task using the accepted 27-piece architecture.
Do not mix those operations.
