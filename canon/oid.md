# oid

status: implementation candidate

## definition

oid is savant's temporal-coherence substrate.

its surviving historical purpose is to prevent independent savant media,
events, projections, and computations from silently fabricating incompatible
versions of "now".

oid does not create one artificial total ordering when reality only supports a
partial ordering.

oid instead provides a deterministic temporal frame in which savant can
distinguish:

- observed time;
- asserted time;
- effective time;
- logical order;
- causal order;
- concurrent order;
- uncertain order;
- interval overlap;
- clock disagreement;
- projection time;
- replay time.

## fundamental law

> oid preserves one coherent temporal frame without inventing chronology that
> the available evidence cannot support.

## authority boundary

oid owns:

- temporal normalization;
- temporal-frame identity;
- logical sequencing inside an oid frame;
- causal temporal constraints;
- temporal uncertainty;
- concurrency representation;
- temporal conflict representation;
- deterministic temporal projection;
- temporal replay coordinates;
- clock-skew representation;
- temporal integrity receipts.

oid does not own:

- factual admission;
- external truth;
- event substance;
- memory;
- identity;
- provider execution;
- persona authority;
- durable canon mutation;
- causal meaning outside temporal relationships.

notary remains responsible for admission and verification where applicable.

coda remains responsible for accepted durable mutation where applicable.

noumenon remains responsible for personal significance and developmental
continuity.

oid temporal ordering never upgrades external authority.

## temporal semantics

oid distinguishes:

event time:
the time attributed to the event itself.

observation time:
the time at which savant observed or received the event.

logical time:
a deterministic sequence coordinate used when wall-clock ordering is
insufficient.

effective time:
the normalized temporal coordinate used by a projection.

interval:
a bounded or partially bounded temporal extent.

concurrency:
two records for which oid has insufficient causal evidence to establish a
strict order.

temporal conflict:
two or more temporal assertions that cannot all be simultaneously satisfied.

unknown:
absence of sufficient temporal information.

## ordering law

oid may derive:

- before;
- after;
- equal;
- overlaps;
- contains;
- contained_by;
- concurrent;
- conflicting;
- unknown.

oid must never convert concurrent or unknown into before/after merely for
convenience.

## replay law

replay uses admitted temporal primitives and their logical coordinates.

replay order is deterministic.

replay order is not automatically a claim about external chronology.

## conversion law

all normalized machine timestamps use utc.

source timezone and original timestamp representations may be preserved as
provenance.

normalization does not erase source representation.

## integrity law

immutable oid records receive deterministic content digests.

mutation creates a successor record or projection rather than silently
rewriting prior temporal evidence.

## advanced implementation requirements

oid supports at minimum:

1. utc normalization.
2. original timestamp preservation.
3. source-clock identity.
4. logical sequence coordinates.
5. monotonic frame sequencing.
6. causal predecessor references.
7. causal successor derivation.
8. partial ordering.
9. explicit concurrency.
10. explicit unknown ordering.
11. temporal intervals.
12. interval overlap detection.
13. temporal conflict detection.
14. clock-skew representation.
15. uncertainty bounds.
16. confidence-independent authority isolation.
17. deterministic content addressing.
18. replay coordinates.
19. deterministic projection.
20. immutable temporal evidence.
21. provenance references.
22. evidence references.
23. authority references.
24. bounded metadata.
25. model independence.
26. provider independence.
27. dependency sovereignty.
28. graceful operation without external clock libraries.
29. deterministic tie handling.
30. temporal integrity receipts.
31. reversible serialization.
32. contradiction preservation.
33. no automatic destructive reconciliation.
34. typed temporal relationships.
35. cross-system temporal-frame compatibility.

## dependency policy

python standard-library datetime and zoneinfo facilities are sufficient for the
canonical initial implementation.

optional future accelerators may improve storage, distributed clock
observation, or telemetry, but no external package may become oid semantic
authority.

## compatibility

historical halo, catena, catax, and other metaphysical structures are not
required by oid.

their historical presence does not grant them current authority.

the surviving oid concept is temporal coherence itself.

## projection rule

oid projections are derived and non-authoritative.

a projection may report temporal conflicts without resolving them.

a projection may report concurrency without forcing serialization.

a projection may establish deterministic replay order while explicitly
distinguishing that replay order from asserted external chronology.
