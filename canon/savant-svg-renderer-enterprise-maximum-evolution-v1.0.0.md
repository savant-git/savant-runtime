# savant svg renderer enterprise maximum-evolution specification

version: 1.0.0\
date: 2026-09-12\
status: accepted-next-task specification\
implementation_state: not_started\
execution_order: after current sdump / migration-packet work\
authority_effect: none until admitted through established savant
authority mechanisms\
working_root: /root/savant-runtime\
task_class: bounded production subsystem evolution\
primary_projection: svg\
canonical_owner: to be resolved from current verified savant
implementation before file placement\
terminology_policy: savant-owned terminology, paths, filenames,
identifiers, and content remain lowercase unless external syntax,
compatibility, or higher authority requires otherwise

------------------------------------------------------------------------

## 0. executive directive

Implement a savant-native, enterprise-grade vector scene compiler whose
primary compatibility projection is standards-compliant svg.

This is not an svg string builder, primitive-shape convenience wrapper,
xml templating library, or collection of ad hoc drawing helpers. The
durable kernel is a semantic vector system that substantiates geometry,
paint, composition, definitions, constraints, text, effects, metadata,
and reusable vector components once, composes them deterministically,
validates the resulting graph, and projects the graph into svg.

The subsystem must be capable of expressing and accurately compiling
extremely complex scenes containing deeply nested groups, compound
paths, reusable instances, sophisticated masks and clips, gradients,
patterns, multi-stage filter graphs, text, text-on-path, transforms,
blend modes, responsive coordinate systems, semantic layers, procedural
geometry, deterministic definitions, and optional advanced computational
geometry.

The governing pipeline is:

``` text
semantic vector primitives
    ↓
canonical geometry and style
    ↓
scene graph
    ↓
instances and typed relationships
    ↓
composition
    ↓
constraints / derived geometry
    ↓
definition dependency graph
    ↓
normalization
    ↓
validation
    ↓
svg projection
    ↓
safe deterministic optimization
    ↓
deterministic serialization
```

The governing savant law remains:

``` text
substantiate once
→ instance
→ compose
→ relate through typed segues
→ project
```

Svg is a projection. It must not become a competing source of truth.

------------------------------------------------------------------------

# part i --- authority, identity, and architectural law

## 1. authority and preservation

Before implementation, inspect only the current verified savant files
necessary to determine:

1.  whether a vector/svg owner already exists;
2.  whether existing svg helpers or renderers exist;
3.  which current savant component owns projection/rendering of this
    class;
4.  which existing primitives must be preserved;
5.  which external interfaces already depend on svg generation.

Do not conduct a broad repository audit.

Current accepted savant authority outranks this specification wherever
they conflict. This document defines the requested subsystem but does
not supersede higher authority by itself.

Preserve:

-   accepted decisions;
-   constitutional canon;
-   verified valid behavior;
-   semantic identity;
-   existing compatibility contracts;
-   deterministic behavior;
-   lineage and provenance;
-   dependencies and dependents;
-   replay and recovery properties;
-   graph addressability;
-   established ownership boundaries;
-   valid external interfaces.

If a simplistic svg implementation already exists, prefer:

``` text
existing interface
→ compatibility adapter
→ canonical vector scene
→ svg compiler
```

rather than destructive replacement.

## 2. irreducible identity

The subsystem is a **vector scene compiler**.

Its canonical substance is not xml.

Its canonical substance consists of semantic vector primitives and
relationships sufficient to deterministically derive svg.

The subsystem owns only the vector semantics necessary to construct and
project vector scenes. It must not become a browser engine, full design
application, cad suite, raster graphics platform, general document
engine, or independent font authority.

## 3. architectural compression

Actively replace collections of weaker mechanisms with stronger reusable
primitives.

Examples:

-   one canonical `paint` abstraction instead of separate unrelated fill
    implementations;
-   one transform algebra instead of per-node transform strings;
-   one definition registry instead of mask/filter/gradient registries
    that independently reinvent identity;
-   one dependency graph for all reusable definitions;
-   one canonical path model for visible paths, clips, masks, text
    paths, and geometry backends;
-   one serialization policy for numeric precision;
-   one resource-reference policy for images, fonts, and external
    references;
-   one validation framework with typed diagnostics instead of scattered
    assertions.

Do not compress concepts whose semantics genuinely differ.

## 4. authoritative versus derived state

Authoritative or canonical scene inputs may include:

-   node identity;
-   geometry;
-   explicit styles;
-   explicit transforms;
-   explicit reusable definitions;
-   explicit relationships;
-   explicit constraints;
-   explicit resource references;
-   explicit animation declarations;
-   explicit metadata.

Derived state includes:

-   bounds;
-   normalized paths;
-   flattened transforms;
-   resolved constraints;
-   generated svg IDs;
-   definition order;
-   definition deduplication;
-   optimized path commands;
-   cached shaped text;
-   serialized svg;
-   raster previews;
-   diagnostics;
-   indexes.

Derived state must be rebuildable.

## 5. identity model

Distinguish:

-   semantic identity;
-   instance identity;
-   definition identity;
-   projection identity;
-   textual svg `id`;
-   content digest.

Never assume these are interchangeable.

A reusable symbol can retain semantic identity while its svg definition
ID is generated deterministically from normalized content or a stable
semantic key.

## 6. lineage and provenance

Where geometry is derived, preserve enough lineage to answer what
operation produced it.

Examples:

``` text
path a + path b
→ boolean difference
→ path c
```

``` text
symbol s
→ instance i
→ transform t
→ projected group g
```

``` text
text run
→ shaping input
→ glyph sequence
→ glyph positioning
→ optional outline projection
```

Production svg need not expose all lineage. Diagnostic projections may
expose it.

------------------------------------------------------------------------

# part ii --- canonical scene model

## 7. scene

A scene is the root semantic vector object.

It should support, as justified:

-   semantic identity;
-   logical width and height;
-   viewbox;
-   coordinate-space policy;
-   preserve-aspect-ratio policy;
-   root transform;
-   root children;
-   reusable definitions/components;
-   metadata;
-   accessibility metadata;
-   resource policy;
-   compilation configuration;
-   optional animation timeline declarations.

A scene must be immutable or effectively immutable by compilation time.

## 8. node protocol

All scene nodes must expose a minimal common semantic contract:

-   node type;
-   optional semantic identity;
-   optional semantic name;
-   optional metadata;
-   optional transform;
-   optional style;
-   optional visibility;
-   optional opacity;
-   optional clip;
-   optional mask;
-   optional filter;
-   optional interaction/accessibility metadata where valid.

Do not force properties onto node types where svg semantics make them
invalid.

## 9. core node families

Support a coherent set including:

-   group;
-   path;
-   rectangle;
-   circle;
-   ellipse;
-   line;
-   polyline;
-   polygon;
-   text;
-   text-path;
-   image;
-   symbol/component;
-   instance/use;
-   mask;
-   clip-path;
-   pattern;
-   linear-gradient;
-   radial-gradient;
-   filter;
-   marker where justified.

Primitive shapes may remain semantic primitives internally and be
projected directly or normalized to paths when an operation requires
canonical path geometry.

## 10. immutable canonical nodes

Prefer frozen dataclasses, immutable records, or equivalent immutable
value objects for canonical nodes.

If ergonomic builders exist, builders are transient. They must finalize
into canonical nodes before compilation.

Shared definitions must not be mutated through one instance.

## 11. extension model

New node types must integrate through stable dispatch/protocol
boundaries.

Avoid a giant serializer function whose complexity grows without bound.

However, do not create a heavyweight plugin system until actual
third-party extension is required.

------------------------------------------------------------------------

# part iii --- geometry kernel

## 12. numeric foundation

Use explicit finite real-number validation.

Reject:

-   NaN;
-   positive infinity;
-   negative infinity.

Normalize negative zero at serialization.

Centralize epsilon/tolerance policy for computational geometry. Do not
scatter arbitrary tolerances.

Distinguish exact semantic values from approximation tolerances
introduced by a geometry backend.

## 13. point and vector

Provide immutable point/vector primitives with justified operations:

-   addition;
-   subtraction;
-   scalar multiplication;
-   dot product;
-   cross product;
-   magnitude;
-   normalization with zero-length protection;
-   interpolation;
-   transformation.

Avoid overloading semantics where it harms clarity.

## 14. affine transform algebra

Provide a first-class affine matrix representation.

Support:

-   identity;
-   translate;
-   scale;
-   rotate;
-   rotate about point;
-   skew-x;
-   skew-y;
-   arbitrary matrix;
-   composition;
-   inversion where nonsingular;
-   point transformation;
-   vector transformation;
-   bounds transformation.

Transform multiplication order must be explicit and tested.

## 15. canonical path commands

Canonical path geometry must support:

-   move-to;
-   line-to;
-   quadratic bezier;
-   cubic bezier;
-   elliptical arc;
-   close-path.

Horizontal, vertical, and smooth svg commands may be accepted by parsers
but should normalize into canonical operations unless preservation
materially improves editability.

## 16. subpaths and compound paths

A path can contain multiple subpaths.

Preserve:

-   subpath boundaries;
-   closure;
-   winding;
-   fill rule.

Support:

-   nonzero;
-   evenodd.

Do not merge subpaths when that can alter winding semantics.

## 17. bezier mathematics

Implement accurate evaluation and extrema calculation for quadratic and
cubic bezier segments.

Required derived operations include:

-   point at parameter;
-   derivative;
-   extrema roots;
-   geometric bounds;
-   tangent where valid;
-   subdivision.

Do not compute curve bounds using control-point or endpoint heuristics
alone when exact polynomial extrema are practical.

## 18. elliptical arcs

Represent arcs canonically with:

-   rx;
-   ry;
-   x-axis rotation;
-   large-arc flag;
-   sweep flag;
-   endpoint.

Provide deterministic endpoint-to-center conversion where required.

Arc-to-bezier conversion is derived geometry and must preserve
approximation tolerance metadata where relevant.

## 19. path normalization

Normalize paths deterministically.

Potential operations:

-   validate command arity;
-   normalize command representation;
-   eliminate semantically inert duplicate moves where safe;
-   canonicalize close behavior;
-   normalize numeric values;
-   preserve fill semantics;
-   preserve explicit semantic segmentation when configured.

## 20. path metrics

Provide derived path metrics when required:

-   segment count;
-   approximate/exact length according to segment type and tolerance;
-   point at length;
-   tangent at length;
-   subpath lengths.

Do not calculate expensive metrics unless requested by text paths,
animation, layout, or diagnostics.

## 21. geometric bounds

Bounds must be derived.

Support:

-   primitive bounds;
-   path bounds;
-   bezier extrema;
-   transformed bounds;
-   group bounds;
-   stroke-aware bounds;
-   marker-aware bounds where markers exist;
-   conservative filter expansion where known;
-   mask/clip coordinate-space considerations.

Cache only against immutable semantic inputs.

## 22. stroke geometry

Canonical stroke semantics should support:

-   paint;
-   width;
-   opacity;
-   line cap;
-   line join;
-   miter limit;
-   dash array;
-   dash offset;
-   vector effect.

Stroke-to-path conversion is an optional derived geometry operation, not
a requirement for ordinary svg projection.

## 23. boolean geometry boundary

Do not implement unreliable general path boolean operations merely to
claim feature coverage.

Expose a backend-neutral contract:

``` text
union
intersection
difference
xor
```

Inputs and outputs use canonical savant path geometry.

Backend-specific types must not escape.

## 24. advanced geometry operations

The backend boundary should permit future support for:

-   path offsetting;
-   stroke expansion;
-   self-intersection cleanup;
-   polygon clipping;
-   contour simplification;
-   curve flattening;
-   intersection enumeration;
-   winding classification.

Only implement operations required by the first production target.

## 25. geometry backend policy

Native deterministic geometry should handle straightforward operations.

A mature external geometry kernel may be adopted for difficult path
operations only after confirming:

-   correctness advantage;
-   compatible license;
-   maintained upstream;
-   deterministic behavior adequate for savant;
-   bounded deployment complexity;
-   isolation behind the geometry interface;
-   no competing scene authority.

Skia PathKit is a candidate backend for robust path operations because
it exposes Skia path capabilities through WebAssembly, but it must
remain optional and isolated rather than defining the canonical scene
model.

------------------------------------------------------------------------

# part iv --- paint, color, and appearance

## 26. paint algebra

Use one paint abstraction with variants such as:

-   none;
-   solid color;
-   current color;
-   linear gradient reference/value;
-   radial gradient reference/value;
-   pattern reference/value;
-   image paint where justified.

Geometry must not contain raw svg paint strings as its primary
representation.

## 27. color model

Support a stable internal color representation sufficient for svg
projection.

At minimum support:

-   srgb;
-   alpha.

Architect the color boundary so wider-gamut/color-space support can be
added without changing geometry.

Current CSS Color specifications define richer color syntax and spaces.
Treat them as external compatibility capabilities, not internal
authority. Do not claim a color form is universally supported by svg
consumers without compatibility evidence.

## 28. gradient model

Linear gradients support:

-   endpoints;
-   units;
-   transform;
-   spread method;
-   ordered stops.

Radial gradients support:

-   center;
-   radius;
-   focal point;
-   focal radius where supported;
-   units;
-   transform;
-   spread method;
-   ordered stops.

Stops support:

-   offset;
-   color;
-   opacity.

Validate stop offsets and deterministic ordering.

## 29. gradient interpolation policy

Keep interpolation/color-space policy explicit where supported.

Do not silently alter colors to compensate for a particular viewer.

## 30. patterns

Patterns are reusable definitions with:

-   geometry;
-   width/height;
-   units;
-   content units;
-   transform;
-   arbitrary scene children.

Patterns participate in the same definition registry and dependency
graph as masks, filters, and gradients.

## 31. style

Separate style from geometry.

Style should represent valid presentation semantics including:

-   fill;
-   fill opacity;
-   fill rule;
-   stroke;
-   stroke opacity;
-   stroke width;
-   stroke cap/join;
-   dash behavior;
-   overall opacity;
-   visibility;
-   display where needed;
-   paint order where supported;
-   vector effect;
-   blend mode.

## 32. style inheritance

Make inheritance explicit in the semantic model or normalize it
deterministically.

Do not rely on accidental Python object nesting to imply css
inheritance.

Provide a resolved-style projection when required for hashing,
diagnostics, or backends.

------------------------------------------------------------------------

# part v --- composition, masks, clips, and effects

## 33. groups

Groups are semantic composition nodes.

Support:

-   ordered children;
-   transform;
-   style inheritance;
-   group opacity;
-   mask;
-   clip;
-   filter;
-   blend mode;
-   isolation;
-   semantic name;
-   metadata.

Group opacity must remain group opacity. Do not distribute it into
children when that changes compositing.

## 34. masks as first-class objects

Masks must never be raw xml fragments.

Support:

-   alpha masks;
-   luminance masks;
-   arbitrary scene children;
-   nested groups;
-   gradients;
-   patterns;
-   images where permitted;
-   transforms;
-   mask units;
-   content units;
-   explicit or derived bounds.

Masks may depend on other definitions.

## 35. nested masking

Support masks applied to nodes whose mask content itself contains masked
or filtered groups where svg semantics permit.

Dependency cycles must be rejected.

Coordinate spaces must remain explicit.

## 36. clip paths

Clip paths are first-class reusable definitions.

Support:

-   paths;
-   compound paths;
-   primitive shapes;
-   groups where valid;
-   transforms;
-   clip units.

Clipping must not be emulated with masks when native clip semantics
suffice.

## 37. compositing and blending

Support compatible blend modes including:

-   normal;
-   multiply;
-   screen;
-   overlay;
-   darken;
-   lighten;
-   color-dodge;
-   color-burn;
-   hard-light;
-   soft-light;
-   difference;
-   exclusion;
-   hue;
-   saturation;
-   color;
-   luminosity.

Support isolation where appropriate.

Keep compositing semantics separate from paint.

## 38. filter graph

Represent filters as directed semantic graphs.

Each filter primitive has:

-   type;
-   parameters;
-   input references;
-   optional result name.

Support a coherent production subset including:

-   gaussian blur;
-   offset;
-   flood;
-   blend;
-   composite;
-   color matrix;
-   component transfer;
-   morphology;
-   turbulence;
-   displacement map;
-   convolution matrix;
-   diffuse lighting;
-   specular lighting;
-   merge;
-   tile;
-   image where policy permits;
-   drop shadow compatibility projection.

## 39. filter inputs

Model standard inputs explicitly where appropriate:

-   source graphic;
-   source alpha;
-   prior named result.

Do not permit arbitrary dangling result names.

## 40. filter graph validation

Validate:

-   primitive type;
-   parameter domains;
-   result-name uniqueness where required;
-   input existence;
-   illegal cycles;
-   resource references;
-   filter bounds.

## 41. filter regions

Filters frequently extend beyond object bounds.

Provide:

-   explicit region;
-   conservative derived expansion for known primitives;
-   user-space/object-bounding-box units.

Do not default to absurdly huge regions.

Do not allow blur/shadow/displacement to be accidentally clipped by
naive bounds.

## 42. markers

Support markers when justified for diagrams and technical drawings.

Markers may attach to:

-   start;
-   mid;
-   end.

Marker geometry is reusable definition substance.

------------------------------------------------------------------------

# part vi --- symbols, instances, and reuse

## 43. symbol/component primitive

A symbol/component can contain an arbitrary vector subtree.

It is substantiated once.

It can expose:

-   semantic identity;
-   viewbox;
-   anchor points;
-   parameterizable style slots where justified;
-   metadata.

## 44. instances

Instances reference symbols/components.

Support:

-   transform;
-   position;
-   scale;
-   rotation;
-   opacity;
-   compatible style overrides;
-   metadata;
-   semantic instance identity.

Do not duplicate symbol children into every canonical instance.

## 45. svg `<use>` projection

Use svg `<symbol>` / `<use>` when it preserves semantics and downstream
compatibility.

If a target has known `<use>` limitations for a feature, the projection
layer may expand an instance deterministically without changing
canonical instance authority.

## 46. structural sharing

Permit internal structural sharing beyond explicit symbols where
immutable canonical nodes make it safe.

Do not expose implementation-level sharing as semantic identity unless
intended.

------------------------------------------------------------------------

# part vii --- definition registry and dependency resolution

## 47. unified definition registry

Use one registry for reusable projection definitions:

-   gradients;
-   patterns;
-   masks;
-   clips;
-   filters;
-   symbols;
-   markers;
-   reusable paths where needed.

Avoid separate identity systems.

## 48. canonical definition hashing

For content-addressed definitions:

1.  normalize semantic content;
2.  serialize to canonical internal form;
3.  exclude transient state;
4.  hash with a stable cryptographic digest;
5.  derive a deterministic projection ID.

Do not hash Python repr output.

## 49. stable semantic IDs

Where explicit stable semantic identity exists, permit a deterministic
semantic-key ID strategy.

Collision policy must be explicit.

## 50. deduplication

Definitions with semantically equivalent canonical content may be
deduplicated.

Do not deduplicate definitions when external identity or animation
semantics require them to remain distinct.

## 51. dependency graph

Definitions can reference definitions.

Build a directed dependency graph.

Required operations:

-   dependency discovery;
-   missing-reference detection;
-   cycle detection;
-   stable topological ordering;
-   deterministic tie-breaking.

## 52. cycle policy

Reject illegal cycles with a typed diagnostic containing the cycle path.

Do not recursively serialize until stack overflow.

## 53. generated ID policy

Generated IDs must be:

-   deterministic;
-   valid for svg;
-   collision-resistant;
-   stable for stable input;
-   compact in production mode where safe;
-   readable in development mode where useful.

Random UUIDs are prohibited for deterministic compilation.

------------------------------------------------------------------------

# part viii --- constraints and layout

## 54. anchor model

Allow nodes/components to expose named anchors:

-   left;
-   right;
-   top;
-   bottom;
-   center;
-   center-x;
-   center-y;
-   baseline;
-   custom named point;
-   path-relative anchor where justified.

## 55. constraint model

Start with deterministic acyclic relationships rather than a heavyweight
general solver.

Examples:

-   align;
-   offset;
-   center-on;
-   place-right-of;
-   match-width;
-   rotate-about-anchor.

Constraints are semantic inputs. Resolved transforms/coordinates are
derived.

## 56. constraint dependency graph

Resolve constraints through explicit dependencies.

Detect cycles.

Provide diagnostics naming the participating nodes/anchors.

## 57. optional advanced solver boundary

If future use cases require linear constraint solving, isolate it behind
a layout backend.

Do not introduce a solver merely for architectural elegance.

------------------------------------------------------------------------

# part ix --- typography

## 58. text as first-class content

Text nodes support:

-   unicode content;
-   position;
-   transform;
-   fill/stroke;
-   opacity;
-   font family;
-   font size;
-   weight;
-   style;
-   stretch where supported;
-   letter spacing;
-   word spacing;
-   text anchor;
-   baseline policy;
-   direction;
-   writing mode where supported;
-   language/script metadata where relevant.

## 59. text shaping boundary

Correct multilingual typography requires shaping, not
character-by-character placement.

A shaping backend should accept:

``` text
unicode text
+ font face
+ size
+ direction
+ script
+ language
+ features
→ positioned glyph run
```

HarfBuzz is a strong candidate for optional production shaping because
its documented core operation converts Unicode buffers into positioned
glyph sequences and handles script/language shaping behavior. It must
remain an implementation backend, not savant authority.

## 60. shaping cache

If shaping is adopted, cache immutable shape plans/results only when
keys fully represent:

-   font identity;
-   font version/digest;
-   text;
-   direction;
-   script;
-   language;
-   features;
-   size-dependent behavior where applicable.

Derived shaping cache must be rebuildable.

## 61. text paths

Support semantic text-path references.

Properties may include:

-   referenced path;
-   start offset;
-   method;
-   spacing;
-   side where supported;
-   text anchor.

The referenced path participates in dependency resolution.

## 62. glyph-level projection

Permit per-glyph positioning/transforms for advanced typography.

Do not require outline conversion for ordinary text.

## 63. text-to-path boundary

Text-to-path conversion requires actual font outlines and shaping.

If implemented:

-   require explicit font resource;
-   shape first;
-   derive glyph outlines;
-   transform outlines into canonical paths;
-   preserve lineage back to text/font/glyph IDs.

Do not pretend generic font-family names are enough for deterministic
outlines.

## 64. font security and portability

Do not silently scan or embed arbitrary system fonts in portable output.

Font use must obey explicit resource policy.

Never package or expose font files without authority.

------------------------------------------------------------------------

# part x --- images and external resources

## 65. image nodes

Support:

-   source reference;
-   x/y;
-   width/height;
-   transform;
-   opacity;
-   preserve-aspect-ratio;
-   clip;
-   mask;
-   filter.

## 66. resource policy

Classify resources:

-   embedded;
-   local;
-   external.

Compilation policy can permit or reject each category.

## 67. no implicit network access

The compiler must not fetch remote images, fonts, stylesheets, or other
resources merely because an svg node references them.

Network resolution belongs to an explicit external resource resolver.

## 68. safe data embedding

If data URIs are supported, validate media type and enforce configurable
size limits.

Do not permit arbitrary script-bearing payloads through an ordinary
image API.

------------------------------------------------------------------------

# part xi --- animation and temporal projection

## 69. animation model

Animation is separate semantic data attached to target properties.

Potential targets:

-   transform;
-   opacity;
-   fill/stroke color;
-   path parameters where supported;
-   filter parameters;
-   mask parameters;
-   dash offset.

## 70. timeline primitives

Support only what is justified:

-   duration;
-   delay/begin;
-   repeat;
-   easing;
-   keyframes;
-   fill behavior.

## 71. projection strategies

Allow projection policy to choose:

-   static first frame;
-   smil where appropriate;
-   css animation where appropriate.

Do not introduce JavaScript execution by default.

## 72. deterministic animation source

Animation declarations must serialize deterministically.

Runtime time progression is external viewer behavior.

------------------------------------------------------------------------

# part xii --- accessibility, semantics, and interaction

## 73. semantic layers

Support semantic grouping independent of incidental serializer
structure.

Examples:

-   background;
-   assembly;
-   annotation;
-   labels;
-   mask-source;
-   interaction-region.

## 74. accessibility

Support where appropriate:

-   title;
-   description;
-   role;
-   aria-compatible metadata;
-   focusability policy where interactive.

## 75. interaction metadata

Optionally support:

-   semantic IDs;
-   classes;
-   data attributes;
-   pointer-events policy;
-   hit-region metadata.

Do not embed executable script in default output.

## 76. hit testing

Provide derived hit-testing geometry only when requested.

Possible policies:

-   fill geometry;
-   stroke geometry;
-   bounding box;
-   explicit interaction path.

Do not bake hit-test artifacts into production svg unless requested.

------------------------------------------------------------------------

# part xiii --- procedural and generative geometry

## 77. deterministic procedural construction

Support procedural builders for:

-   grids;
-   repeated motifs;
-   radial arrays;
-   stars;
-   regular polygons;
-   spirals;
-   waveforms;
-   parametric curves;
-   transformed repetitions.

Builders emit canonical geometry/instances.

## 78. seeded randomness

Any stochastic-looking construction must require an explicit seed.

Use a documented deterministic PRNG policy.

Seed becomes semantic input.

System randomness must not affect replayable scene geometry.

## 79. expansion limits

Procedural builders must respect resource limits:

-   maximum generated nodes;
-   maximum path segments;
-   maximum recursion depth where recursive patterns exist.

Fail explicitly rather than exhausting memory.

------------------------------------------------------------------------

# part xiv --- validation and diagnostics

## 80. typed validation errors

Define typed errors such as:

-   scene validation error;
-   geometry error;
-   transform error;
-   reference error;
-   dependency-cycle error;
-   constraint-cycle error;
-   resource-policy error;
-   filter error;
-   unsupported-feature error;
-   serialization error;
-   geometry-backend error;
-   shaping-backend error.

## 81. diagnostic path

Every error should identify a semantic location such as:

``` text
scene/root/group[logo]/mask[cutout]/path[3]
```

Avoid opaque "invalid svg" errors.

## 82. construction validation

Reject obviously malformed values near construction where inexpensive.

Examples:

-   non-finite numbers;
-   negative radius where invalid;
-   malformed color values if using structured color;
-   invalid enum values.

## 83. graph validation

Before projection validate:

-   reference existence;
-   definition dependencies;
-   illegal cycles;
-   constraint cycles;
-   instance targets;
-   mask/clip/filter targets;
-   text-path targets.

## 84. projection validation

Before final serialization validate:

-   all generated references resolve;
-   all generated IDs are unique;
-   namespaces are present;
-   no unsafe raw markup entered through safe APIs;
-   numeric serialization is finite;
-   projection policy requirements are met.

## 85. diagnostic projection

Provide an optional diagnostic mode that may emit:

-   semantic node IDs;
-   bounds;
-   definition IDs;
-   dependency information;
-   lineage hints;
-   compilation digest.

Diagnostic metadata is derived and must not become required scene
substance.

------------------------------------------------------------------------

# part xv --- security

## 86. safe xml serialization

Centralize escaping for:

-   text;
-   attributes;
-   IDs;
-   metadata.

Never interpolate untrusted values directly into markup.

## 87. raw xml escape hatch

Prefer no raw xml API.

If unavoidable for compatibility, name it explicitly unsafe and keep it
outside ordinary scene construction.

Unsafe fragments must not silently participate in trusted deterministic
hashing without explicit normalization policy.

## 88. url policy

Validate url-bearing attributes.

Support an allowlist policy for schemes.

Default portable/security-sensitive modes should reject dangerous or
unexpected external schemes.

## 89. script policy

Do not emit `<script>` from ordinary scene APIs.

Scripted svg is outside the default renderer boundary.

## 90. entity and parser safety

If svg input parsing is later implemented:

-   prohibit dangerous external entity behavior;
-   do not resolve arbitrary network entities;
-   bound input size;
-   bound nesting;
-   validate references.

Svg output generation itself should not require a permissive xml parser.

## 91. resource exhaustion

Protect compilation against malicious or accidental explosions
involving:

-   recursive instances;
-   recursive definitions;
-   huge procedural expansions;
-   pathological filter graphs;
-   enormous path segment counts;
-   oversized embedded resources.

Use configurable, defensible resource budgets.

## 92. file writes

When writing final svg:

1.  serialize to temporary destination or safe buffer;
2.  validate completion;
3.  fsync where the existing savant persistence policy requires it;
4.  atomically replace destination.

Do not leave partial final files.

## 93. path safety

Any file-writing API must enforce destination policy and avoid traversal
outside authorized roots where a sandbox/root policy exists.

------------------------------------------------------------------------

# part xvi --- deterministic compiler

## 94. compilation context

Use ephemeral compilation context containing:

-   canonical scene;
-   configuration;
-   definition registry;
-   dependency graph;
-   generated IDs;
-   caches;
-   diagnostics;
-   geometry backend;
-   text shaping backend;
-   resource resolver.

The context is disposable.

## 95. compilation phases

Recommended deterministic phases:

1.  accept canonical scene;
2.  validate local invariants;
3.  normalize geometry;
4.  normalize style;
5.  resolve constraints;
6.  collect definitions;
7.  build definition dependency graph;
8.  validate dependencies;
9.  deduplicate eligible definitions;
10. assign deterministic IDs;
11. derive required bounds/metrics;
12. resolve backend-derived geometry;
13. validate resolved scene;
14. project svg element tree;
15. apply safe projection optimizations;
16. serialize deterministically;
17. compute compilation digest;
18. optionally atomically persist.

Phases may be compressed in implementation if semantics remain explicit.

## 96. deterministic ordering

Control:

-   root child order;
-   definition order;
-   attribute order;
-   metadata order;
-   class/style order;
-   generated IDs;
-   filter result names;
-   serialization whitespace;
-   number formatting.

Never rely on unordered traversal.

## 97. canonical internal serialization

Provide a canonical semantic encoding for hashing.

Properties:

-   stable key ordering;
-   stable type tags;
-   normalized numbers;
-   explicit null/absence policy;
-   no memory addresses;
-   no runtime timestamps unless they are semantic inputs;
-   no nondeterministic object IDs.

## 98. digest

Compute a stable digest over:

-   normalized scene semantics;
-   relevant compiler configuration;
-   backend identity/version where backend results affect output;
-   resource digests where embedded/resolved resources affect output.

This supports replay and cache correctness.

## 99. backend fingerprinting

When optional geometry or shaping backends materially affect output,
include backend identity/version in derived cache keys and compilation
provenance.

Do not claim byte stability across materially different backends unless
proven.

------------------------------------------------------------------------

# part xvii --- serializer and optimization

## 100. centralized number formatting

One formatter owns floating-point projection.

Readable mode:

-   conventional decimal representation;
-   stable precision;
-   no unnecessary noise.

Production mode:

-   deterministic rounding;
-   trailing-zero removal;
-   negative-zero normalization;
-   compact leading-zero policy where legal.

## 101. readable mode

Readable output should provide:

-   indentation;
-   stable line breaks;
-   meaningful generated IDs where practical;
-   semantic grouping;
-   useful accessibility/metadata;
-   predictable attribute order.

## 102. production mode

Production output should provide:

-   minimal whitespace;
-   compact numbers;
-   deduplicated definitions;
-   stable compact IDs where safe;
-   safe path-command optimization;
-   unnecessary diagnostic metadata removed;
-   reusable instances preserved where beneficial.

## 103. diagnostic mode

Diagnostic output can prioritize inspection over compactness.

It may include comments or metadata only if safely serialized and
explicitly enabled.

## 104. path command optimization

Safe optimizations may include:

-   redundant command removal;
-   compatible segment merging;
-   command-letter omission where svg grammar permits and readability
    mode is not required;
-   relative versus absolute choice when deterministically smaller;
-   repeated command compression;
-   safe precision reduction under configured error budget.

Never simplify geometry beyond the configured fidelity contract.

## 105. transform optimization

Collapse transform chains only when:

-   mathematical equivalence is preserved;
-   animation does not target intermediate transforms;
-   semantic editability policy permits it;
-   downstream behavior remains equivalent.

## 106. definition optimization

Deduplicate only semantically equivalent definitions.

Remove unreachable definitions in production projection.

Keep explicit definitions when external identity is semantically
required.

## 107. css optimization

Prefer presentation attributes or deterministic inline style for
predictable portability.

If shared stylesheet generation provides substantial size benefit:

-   derive stable classes;
-   deduplicate styles;
-   scope generated names;
-   preserve inheritance semantics.

Do not make css generation a separate authority.

------------------------------------------------------------------------

# part xviii --- performance and scale

## 108. asymptotic discipline

Avoid repeated full-scene scans where compilation can accumulate
information in one pass.

Use explicit indexes for:

-   semantic IDs;
-   definition references;
-   dependency edges;
-   instances;
-   resource references.

## 109. lazy derived computation

Calculate expensive derived information only when needed:

-   path length;
-   detailed bounds;
-   text shaping;
-   boolean geometry;
-   raster previews.

## 110. memoization

Memoize immutable derived results keyed by semantic digest and relevant
configuration.

Do not cache mutable objects that can invalidate silently.

## 111. streaming serialization

For very large scenes, support streaming final serialization after
definition resolution.

Do not require building multiple complete xml copies in memory.

## 112. bounded concurrency

Only introduce concurrency for expensive independent work such as:

-   shaping many independent text runs;
-   backend geometry operations;
-   resource digesting.

Output order must remain deterministic.

Concurrency must be bounded.

## 113. backpressure and budgets

Compilation configuration may define:

-   maximum scene nodes;
-   maximum definitions;
-   maximum path commands;
-   maximum filter primitives;
-   maximum procedural expansion;
-   maximum embedded bytes;
-   maximum output bytes;
-   maximum backend operation complexity.

On budget failure, return an explicit typed error. Never silently
truncate semantic artwork.

## 114. incremental compilation

Architect for future incremental recompilation by keeping
node/definition digests stable.

Do not implement a complex incremental engine unless a real workload
requires it.

------------------------------------------------------------------------

# part xix --- resilience and recovery

## 115. failure atomicity

Compilation failure must not mutate the canonical scene.

File-output failure must not corrupt an existing valid destination.

## 116. cache corruption

Derived caches must be discardable.

If a cache entry fails integrity/version checks, recompute it.

## 117. versioned canonical schema

Version the canonical scene serialization used for persistence or
interchange.

Schema evolution must be deterministic and reversible where practical.

Do not tie schema version to arbitrary package release numbers without
semantic need.

## 118. unknown features

When reading future/persisted scene data, unknown node/features must
fail explicitly or be preserved as opaque compatibility data only if a
safe policy exists.

Do not silently drop unknown semantics.

## 119. retries

Pure compilation should be safely repeatable.

External resource resolution, if enabled, must distinguish retryable
provider/network failures from semantic scene failures.

------------------------------------------------------------------------

# part xx --- interoperability

## 120. svg standards boundary

Use W3C svg specifications and related standards as the external
compatibility reference for svg syntax/processing semantics.

Do not copy the external schema wholesale into internal architecture.

## 121. feature profiles

Define explicit output compatibility profiles if needed, for example:

-   modern-browser-static;
-   portable-static;
-   editable;
-   animated;
-   strict-no-external-resources.

Profiles are projection policies, not separate scene models.

## 122. resvg/usvg compatibility option

A raster/validation adapter may optionally use a mature renderer such as
resvg/usvg for focused static-svg compatibility checks or raster
preview.

This is optional.

It must not become the canonical scene representation.

A renderer that supports a static subset cannot be used as evidence that
all svg 2/animation features are universally supported.

## 123. pathkit option

PathKit may be considered for difficult path operations.

Adoption requires a focused dependency decision at implementation time.

The canonical geometry interface must work even if PathKit is
unavailable, with unsupported advanced operations failing explicitly.

## 124. harfbuzz option

HarfBuzz may be considered for high-fidelity shaping.

Adoption is justified only when the subsystem actually needs
deterministic shaped glyph positioning rather than browser-native text
layout.

## 125. raster preview boundary

Raster preview is a derived compatibility projection:

``` text
canonical scene
→ svg
→ raster backend
→ png preview
```

It must not become required authority.

## 126. import boundary

Svg import is not required for the first implementation.

If later implemented:

``` text
external svg
→ secure parser
→ validation
→ normalization
→ canonical savant vector primitives
```

Do not retain raw external DOM as internal authority.

------------------------------------------------------------------------

# part xxi --- enterprise observability without observability sprawl

## 127. compilation receipt

Optionally produce a small deterministic compilation receipt containing:

-   scene digest;
-   compiler version;
-   compatibility profile;
-   backend fingerprints;
-   node count;
-   definition count;
-   deduplication count;
-   output bytes;
-   output digest;
-   warnings;
-   success/failure status.

The receipt is evidence, not scene authority.

## 128. metrics

Expose lightweight metrics only when useful:

-   compile duration;
-   normalization duration;
-   backend geometry duration;
-   shaping duration;
-   serialization duration;
-   cache hits/misses;
-   output size.

Do not build a telemetry platform for this subsystem.

## 129. structured warnings

Warnings should be typed and machine-readable.

Examples:

-   compatibility downgrade;
-   unsupported optional feature;
-   external resource omitted;
-   approximation applied;
-   font fallback used;
-   filter region conservatively expanded.

Warnings must not hide correctness failures.

------------------------------------------------------------------------

# part xxii --- advanced capabilities

## 130. mesh-gradient strategy

Native svg mesh-gradient support is not a safe universal assumption.

Represent advanced gradient meshes, if introduced, as a semantic paint
type with projection strategies:

-   native when target profile explicitly supports it;
-   deterministic tessellation/patch approximation;
-   raster fallback only when explicitly allowed.

Do not fake universal support.

## 131. variable-width strokes

Represent variable stroke profiles semantically if required.

Projection strategies may include:

-   derived outline geometry;
-   backend-specific expansion.

Keep original centerline and stroke profile as semantic source.

## 132. morphing

Path morph animation requires compatible topology or deterministic
normalization.

Do not silently morph unrelated command structures.

A future morph normalizer may derive compatible paths while preserving
source lineage.

## 133. clipping versus boolean geometry

Prefer native clipping when the requirement is visibility clipping.

Do not perform destructive boolean intersection merely to emulate a clip
unless target compatibility requires it.

## 134. masking versus opacity geometry

Prefer semantic masks for soft/translucent visibility.

Do not bake mask effects into duplicated path geometry when svg masks
preserve the intended semantics.

## 135. filters versus rasterization

Keep filters vector/semantic where supported.

Rasterize only under an explicit fallback policy.

## 136. reusable effect stacks

Permit reusable effect definitions or composable filter graphs.

Do not copy identical filter chains across nodes.

## 137. parametric components

A component may expose typed parameters that deterministically derive
its canonical subtree.

Parameters must be explicit semantic inputs.

Generated subtree remains derived from component definition plus
parameter set.

## 138. design tokens

If savant already owns design tokens, vector paint/style should
reference that authority rather than duplicate token definitions.

If no such authority exists, do not invent a global design-token system
solely for this renderer.

## 139. snapping and quantization

Optional projection/layout snapping may support:

-   pixel-grid snapping;
-   half-pixel alignment;
-   custom grids.

Snapping must be explicit and never silently mutate canonical geometry.

## 140. coordinate precision budgets

Allow separate precision policy for:

-   semantic storage;
-   computational geometry;
-   final serialization.

Do not reduce internal precision merely because output can be compact.

## 141. large-scene partitioning

For extremely large scenes, permit semantic layers or groups to compile
independently where dependency analysis proves isolation.

Do not fragment scenes prematurely.

## 142. deterministic symbol instancing

Instance expansion, when required by a compatibility profile, must be
deterministic and preserve instance lineage in diagnostic metadata.

## 143. marker and arrow systems

Technical diagrams often require robust markers.

Support reusable marker definitions with orientation, units, ref points,
and viewbox semantics where justified.

## 144. geometry annotations

Diagnostic mode may project control points, bounds, anchors, and
tangents.

These are derived overlays and never production authority.

## 145. clipping diagnostics

Diagnostic mode may visualize clip/mask bounds to expose accidental
clipping.

Do not emit these overlays in normal output.

## 146. filter diagnostics

Diagnostic mode may expose filter regions and primitive graph order.

## 147. scene diffing

A future semantic diff can compare canonical scene digests/subtrees.

Do not diff serialized svg text as the primary semantic comparison.

## 148. canonical scene serialization

If scene persistence is needed, use a deterministic, versioned
serialization format.

Json is acceptable if normalized and schema-controlled.

Do not persist arbitrary Python pickle as portable authority.

## 149. schema validation

If a persisted scene schema is introduced, provide explicit schema
validation.

External schema tooling may assist validation but does not own
semantics.

## 150. deterministic migrations

Persisted schema migrations must:

-   identify source version;
-   identify target version;
-   preserve semantic content;
-   be replayable;
-   avoid destructive overwrite without recovery.

------------------------------------------------------------------------

# part xxiii --- explicit anti-patterns

## 151. prohibited raw-string architecture

Do not build the renderer around repeated:

``` python
svg += "<path ...>"
```

Markup exists only at the projection boundary.

## 152. prohibited duplicate registries

Do not create independent ID registries for every definition type if one
typed registry can safely own all definitions.

## 153. prohibited random IDs

Do not use random UUIDs for normal generated svg IDs.

## 154. prohibited mutable shared definitions

Do not mutate a shared gradient/mask/filter because one instance needs a
variation.

Create a derived definition or parameterized instance.

## 155. prohibited hidden resource loading

Do not fetch remote resources implicitly.

## 156. prohibited silent degradation

Do not silently remove unsupported filters, masks, fonts, animations, or
geometry.

Return a warning only when the configured compatibility policy
explicitly permits degradation. Otherwise fail.

## 157. prohibited blanket rasterization

Do not rasterize complex vector content simply because implementation is
difficult.

## 158. prohibited approximate boolean claims

Do not advertise robust boolean geometry unless the chosen
algorithm/backend actually supports the required cases.

## 159. prohibited serializer authority

Do not let optimized svg text become the canonical editable source.

## 160. prohibited destructive optimization

Do not flatten groups, transforms, symbols, or paths when doing so
changes semantics, animation targets, accessibility, editability
requirements, or reuse.

## 161. prohibited uncontrolled randomness

No geometry may depend on uncontrolled randomness when deterministic
replay is expected.

## 162. prohibited font guessing for outlines

Do not generate deterministic glyph outlines from a family name without
a resolved font resource.

## 163. prohibited broad dependency adoption

Do not add libraries for convenience when the standard library/current
stack suffices.

------------------------------------------------------------------------

# part xxiv --- minimum twenty meaningful enterprise enhancements

The evolved subsystem contains well over twenty legitimate improvements.
The implementation should preserve those that survive current savant
authority and actual requirements.

1.  canonical immutable scene graph;
2.  semantic identity distinct from svg ID;
3.  canonical path algebra;
4.  accurate bezier extrema bounds;
5.  first-class affine transform algebra;
6.  compound path and winding preservation;
7.  unified paint abstraction;
8.  structured modern color boundary;
9.  reusable gradients;
10. reusable patterns;
11. first-class masks;
12. nested masking;
13. first-class clip paths;
14. compositing and blend modes;
15. first-class filter graph;
16. filter dependency validation;
17. filter-region management;
18. unified definition registry;
19. deterministic definition hashing;
20. semantic definition deduplication;
21. dependency graph and stable topological ordering;
22. symbols/components;
23. nonduplicative instances;
24. deterministic instance expansion fallback;
25. canonical bounds engine;
26. stroke-aware bounds;
27. path normalization;
28. safe path optimization;
29. centralized numeric precision;
30. responsive viewbox projection;
31. anchors and deterministic constraints;
32. semantic layers;
33. first-class text;
34. text paths;
35. optional harfbuzz-quality shaping boundary;
36. glyph-level projection;
37. optional text-to-path lineage;
38. explicit resource policy;
39. no implicit network resolution;
40. animation semantic layer;
41. accessibility metadata;
42. interaction metadata;
43. deterministic procedural geometry;
44. seeded generative construction;
45. resource budgets;
46. safe xml serialization;
47. url/script security policy;
48. atomic file output;
49. typed validation errors;
50. semantic diagnostic paths;
51. deterministic compiler phases;
52. canonical semantic hashing;
53. backend fingerprinting;
54. readable projection;
55. production projection;
56. diagnostic projection;
57. stable compilation digest;
58. lazy derived computation;
59. deterministic memoization;
60. streaming serialization;
61. bounded concurrency;
62. cache rebuildability;
63. versioned persisted scene schema boundary;
64. deterministic schema migration boundary;
65. optional robust geometry backend;
66. optional PathKit adapter;
67. optional resvg/usvg compatibility/raster adapter;
68. optional HarfBuzz shaping adapter;
69. lightweight compilation receipts;
70. structured compatibility warnings;
71. mesh-gradient projection strategy;
72. variable-width stroke architecture;
73. morph-normalization boundary;
74. reusable effect stacks;
75. parametric components;
76. explicit snapping policy;
77. separate internal/output precision budgets;
78. large-scene partitioning capability;
79. markers for technical diagrams;
80. diagnostic geometry overlays.

Do not implement a feature merely because it appears in this list.
Implement it when it belongs to the coherent production target.

------------------------------------------------------------------------

# part xxv --- contemporary external leverage decisions

## 164. standards

Use current W3C svg specifications and related masking, filter,
compositing, transforms, geometry, and color specifications as
compatibility references.

These standards define external behavior, not savant internal
architecture.

## 165. resvg/usvg

Potential value:

-   independent static-svg rendering check;
-   raster preview;
-   normalization insight;
-   strong handling of many svg edge cases.

Constraint:

-   static subset orientation means it cannot establish correctness for
    every animation or svg 2 feature.

Decision:

-   optional adapter;
-   do not require for canonical compilation;
-   adopt only if already available or if focused integration benefit
    exceeds dependency cost.

## 166. PathKit / Skia

Potential value:

-   robust mature path operations;
-   difficult boolean geometry;
-   curve/path algorithms.

Decision:

-   optional geometry backend;
-   do not make wasm mandatory for ordinary scene compilation;
-   canonical path model remains savant-owned.

## 167. HarfBuzz

Potential value:

-   correct script-aware shaping;
-   glyph substitution;
-   positioning;
-   direction/script/language-aware layout.

Decision:

-   strong candidate when deterministic high-fidelity typography is
    required;
-   not mandatory for browser-native text projection;
-   isolate behind shaping interface.

## 168. standard library

Prefer standard-library facilities for:

-   dataclasses/value objects;
-   hashing;
-   deterministic json;
-   xml escaping/building where adequate;
-   graph algorithms where straightforward;
-   atomic filesystem operations;
-   math.

Do not add a dependency merely to implement topological sorting,
hashing, or basic xml generation.

------------------------------------------------------------------------

# part xxvi --- compatibility profiles

## 169. modern-browser-static

Purpose:

-   high-capability static svg;
-   masks;
-   filters;
-   gradients;
-   patterns;
-   symbols;
-   modern styling where established.

No script.

## 170. portable-static

Purpose:

-   maximize portability;
-   no external network resources;
-   conservative feature set;
-   embedded/normalized resources where authorized.

## 171. editable

Purpose:

-   preserve semantic groups;
-   preserve readable IDs;
-   avoid destructive flattening;
-   favor tool editability over minimum bytes.

## 172. production-compact

Purpose:

-   deterministic compact output;
-   definition deduplication;
-   safe path optimization;
-   minimal metadata;
-   no diagnostic overlays.

## 173. diagnostic

Purpose:

-   expose semantic IDs;
-   bounds;
-   anchors;
-   definition dependencies;
-   lineage hints;
-   compiler metadata.

## 174. animated

Purpose:

-   preserve declared animation;
-   explicit target capability;
-   fail or warn according to compatibility policy when unsupported.

------------------------------------------------------------------------

# part xxvii --- proposed savant-native module boundaries

The exact filesystem location must be resolved from verified current
ownership before implementation.

Use the smallest coherent module set. A likely conceptual decomposition
is:

``` text
vector/
    model.py
    geometry.py
    path.py
    transform.py
    paint.py
    effects.py
    definitions.py
    constraints.py
    text.py
    validation.py
    compiler.py
    svg.py
    backends/
        geometry.py
        shaping.py
        raster.py
```

This is not authority for the final path.

Architectural roles:

### model

Canonical scene/node/component/instance types.

### geometry

Points, vectors, bounds, affine math, curve math.

### path

Canonical path segments, normalization, metrics.

### transform

Affine transform construction/composition if not compressed into
geometry.

### paint

Colors, gradients, patterns, styles.

### effects

Masks, clips, filters, compositing.

### definitions

Unified registry, hashing, dependency graph, deterministic IDs.

### constraints

Anchors and deterministic layout relationships.

### text

Text runs, text paths, shaping abstraction.

### validation

Typed diagnostics and graph validation.

### compiler

Compilation phases and ephemeral context.

### svg

Svg element projection and deterministic serialization.

### backends

Optional external capability boundaries only.

If fewer files preserve clarity and ownership, use fewer.

------------------------------------------------------------------------

# part xxviii --- canonical conceptual api

The final api should be idiomatic for the implementation language. The
following is conceptual, not binding syntax.

``` python
scene = Scene(
    view_box=ViewBox(0, 0, 1600, 900),
    children=[
        Group(
            name="assembly",
            children=[
                Instance(
                    component=gear,
                    transform=Transform.translate(300, 450),
                ),
                Instance(
                    component=gear,
                    transform=(
                        Transform.translate(700, 450)
                        @ Transform.rotate(0.35)
                        @ Transform.scale(1.25)
                    ),
                ),
            ],
            mask=Mask(
                mode="luminance",
                children=[
                    Circle(
                        center=Point(600, 450),
                        radius=360,
                        fill=RadialGradient(...),
                    ),
                ],
            ),
            filter=FilterGraph(
                primitives=[
                    Turbulence(..., result="noise"),
                    DisplacementMap(
                        source=SourceGraphic,
                        displacement="noise",
                        scale=14,
                        result="distorted",
                    ),
                    GaussianBlur(
                        source="distorted",
                        std_deviation=0.8,
                    ),
                ],
            ),
            blend_mode="multiply",
        ),
    ],
)
```

Compilation:

``` python
compiler = SvgCompiler(
    profile="production-compact",
    precision=6,
)

result = compiler.compile(scene)

result.svg
result.digest
result.receipt
result.warnings
```

The caller should not manually manage `<defs>` IDs.

------------------------------------------------------------------------

# part xxix --- focused enterprise proof scene

## 175. proof objective

Create one deterministic complex scene that proves the kernel rather
than dozens of shallow unit examples.

The scene should include:

-   responsive viewbox;
-   semantic root layers;
-   reusable symbol/component;
-   at least three transformed instances;
-   compound path;
-   cubic bezier;
-   elliptical arc;
-   linear gradient;
-   radial gradient;
-   pattern;
-   alpha or luminance mask;
-   nested clip;
-   group opacity;
-   blend mode;
-   filter graph with at least three stages;
-   reusable marker if implemented;
-   text label;
-   text path if shaping/text support is in first slice;
-   deterministic IDs;
-   content deduplication;
-   readable output;
-   production output.

## 176. determinism proof

Compile the same canonical scene twice with identical configuration.

Require:

``` text
svg_a == svg_b
digest_a == digest_b
```

unless an explicitly documented backend prevents byte equality, in which
case the implementation must be corrected or the deterministic contract
narrowed with authority before completion.

## 177. reference integrity proof

Parse or inspect generated output sufficiently to establish:

-   all `url(#id)` references resolve;
-   all `<use>` references resolve;
-   all text-path references resolve;
-   generated IDs are unique.

## 178. compatibility proof

Use one available standards-capable renderer/browser or optional static
renderer to establish that the representative output is consumable.

Do not infer universal compatibility from one renderer.

------------------------------------------------------------------------

# part xxx --- implementation slices

## 179. slice one: durable kernel

Implement first:

1.  immutable scene model;
2.  geometry primitives;
3.  canonical path;
4.  transforms;
5.  bounds;
6.  style/paint;
7.  gradients;
8.  groups;
9.  symbols and instances;
10. masks;
11. clips;
12. filter graph core;
13. definition registry;
14. dependency graph;
15. deterministic IDs;
16. validation;
17. compiler;
18. readable serializer;
19. production serializer;
20. focused complex proof.

This slice must already be genuinely useful.

## 180. slice two: justified advanced capability

After slice one is proven, add only what the target requires from:

-   boolean geometry backend;
-   path intersections;
-   stroke expansion;
-   HarfBuzz shaping;
-   text outlines;
-   advanced patterns;
-   markers;
-   procedural builders;
-   animation;
-   mesh approximations;
-   variable strokes.

Do not add them merely to increase feature count.

## 181. slice three: integration

Integrate with existing savant consumers only after the canonical kernel
is stable.

Preserve existing interfaces through adapters where required.

------------------------------------------------------------------------

# part xxxi --- minimum validation budget

## 182. syntax / compilation

Validate only changed/new files.

## 183. focused functional check

Run the complex proof scene.

Require:

-   successful compile;
-   deterministic duplicate compile;
-   reference integrity;
-   output file creation.

## 184. integration check

Only if an existing savant svg consumer is changed:

-   invoke one existing consumer path;
-   verify compatible output/use.

Do not run broad unrelated test suites automatically.

------------------------------------------------------------------------

# part xxxii --- enterprise completion gates

The subsystem is not complete until all applicable gates pass.

## 185. authority gate

-   owner/path resolved from current savant authority;
-   no duplicate owner created;
-   existing valid interfaces preserved.

## 186. semantic gate

-   svg remains projection;
-   canonical scene exists independently;
-   reusable substance is not duplicated;
-   definitions are semantic objects.

## 187. geometry gate

-   canonical path works;
-   transforms are correct;
-   bezier bounds are accurate;
-   compound paths preserve fill semantics.

## 188. composition gate

-   groups compose;
-   symbols/instances reuse substance;
-   masks work;
-   clips work;
-   filters work;
-   blend/opacity semantics remain correct.

## 189. definition gate

-   deterministic IDs;
-   dependency graph;
-   missing references detected;
-   cycles detected;
-   deduplication safe.

## 190. security gate

-   safe escaping;
-   no ordinary raw-markup injection;
-   no implicit network fetch;
-   resource budgets;
-   atomic file output where files are written.

## 191. determinism gate

-   repeated compile produces identical output for identical
    inputs/config/backend;
-   stable digest;
-   stable definition ordering.

## 192. resilience gate

-   failure preserves canonical scene;
-   derived caches rebuild;
-   partial output cannot replace valid final output.

## 193. performance gate

-   no obvious quadratic full-scene behavior where avoidable;
-   expensive derived calculations lazy/cached where justified;
-   large output can avoid unnecessary duplicate materialization.

## 194. interoperability gate

-   representative svg is accepted by at least one relevant
    renderer/viewer;
-   compatibility claims remain scoped to evidence.

## 195. preservation gate

-   no known existing valid behavior removed;
-   no hidden second authority;
-   no unnecessary dependency.

------------------------------------------------------------------------

# part xxxiii --- final optimization interrogation

Before stopping, challenge the implementation with all of the following:

1.  Is any geometry stored twice without semantic need?
2.  Are masks/filters/clips semantic or merely disguised xml?
3.  Is any svg ID random?
4.  Can every derived definition be rebuilt?
5.  Are backend-specific objects leaking upward?
6.  Does style duplicate geometry responsibility?
7.  Can a symbol be instantiated without copying its subtree?
8.  Are definition dependencies explicit?
9.  Can malformed cycles fail safely?
10. Can a path contain multiple subpaths without losing winding?
11. Are cubic/quadratic bounds mathematically derived?
12. Is arc conversion deterministic?
13. Is negative zero normalized?
14. Can non-finite coordinates enter output?
15. Can text inject markup?
16. Can a remote image trigger network access implicitly?
17. Can a filter graph reference a nonexistent result?
18. Can a mask accidentally switch coordinate spaces?
19. Can optimization change group-opacity semantics?
20. Can transform flattening break animation?
21. Can deduplication merge semantically distinct animated definitions?
22. Can a cache survive backend version changes incorrectly?
23. Can concurrency reorder output?
24. Can procedural geometry become nondeterministic?
25. Can a huge scene exhaust memory before resource limits engage?
26. Can a failed file write destroy a valid prior svg?
27. Does a dependency exist only for convenience?
28. Is any subsystem duplicated elsewhere in savant?
29. Can readable and production projections derive from one scene?
30. Can diagnostic metadata be removed without changing artwork?
31. Does the renderer remain useful without optional backends?
32. Can optional backends be replaced without changing canonical data?
33. Is external svg behavior normalized at the boundary?
34. Are compatibility claims narrower than or equal to actual evidence?
35. Is the implementation substantially stronger than a string-based svg
    helper?
36. Is any abstraction present solely because it looks architecturally
    neat?
37. Is any feature present without a credible use case?
38. Is lineage lost during boolean/path derivation?
39. Are resource digests part of deterministic output when resources
    affect output?
40. Does the result remain recognizably savant-native?

Correct material weaknesses before declaring completion.

------------------------------------------------------------------------

# part xxxiv --- server execution directive

When this task becomes active:

1.  read only current files necessary to resolve renderer ownership and
    existing svg interfaces;
2.  preserve current implementation;
3.  select the minimum coherent file set;
4.  implement slice one directly;
5.  add optional backends only when their capability is required;
6.  perform syntax/compilation validation;
7.  run the one complex deterministic proof;
8.  run one integration check only if an existing consumer was modified;
9.  stop when the enterprise completion gates pass.

For savant-owned files:

-   use lowercase names;
-   use absolute paths;
-   use nano;
-   provide complete files;
-   never provide patches;
-   never provide fragments;
-   never use placeholders;
-   never use ellipses in place of implementation;
-   never require manual merges;
-   never create files with heredocs or shell redirection.

Do not ask for routine successful output.

Require pasted output only when failure evidence is necessary to
determine the next action.

------------------------------------------------------------------------

# part xxxv --- bounded stopping condition

Stop when the vector kernel can deterministically represent, validate,
reuse, compose, and project sophisticated vector scenes into secure,
standards-compliant svg with:

-   canonical scene semantics;
-   accurate geometry;
-   reusable components;
-   first-class masks;
-   first-class clips;
-   gradients/patterns;
-   filter graphs;
-   deterministic definitions;
-   safe serialization;
-   readable and production projections;
-   resource safety;
-   deterministic replay;
-   scoped interoperability evidence.

Do not continue into a full graphics application merely because more
features are imaginable.

The target is maximum justified capability with minimum unjustified
machinery.

------------------------------------------------------------------------

# part xxxvi --- implementation acceptance statement

The intended end state is:

> savant owns a deterministic semantic vector scene model. Complex
> artwork is substantiated once, instantiated and composed through
> explicit reusable primitives, related through explicit dependencies
> and typed relationships, and projected into svg. Masks, clips,
> filters, gradients, symbols, text, effects, and geometry are
> first-class semantic objects rather than manually synchronized xml.
> Derived state is rebuildable. Output is deterministic, safe, compact
> when requested, inspectable when requested, and interoperable through
> explicit compatibility boundaries.

That is the durable kernel.

------------------------------------------------------------------------

# appendix a --- current external research notes

These notes are implementation evidence, not savant authority.

## a.1 w3c svg

The W3C SVG specification family remains the external standards
reference for scalable vector graphics. SVG 2 defines two-dimensional
vector and mixed vector/raster graphics and its processing model is
broader than merely emitting XML syntax.

Implementation consequence:

-   use W3C semantics as the compatibility target;
-   keep the savant scene model independent of W3C document-object
    architecture.

## a.2 related w3c graphics specifications

The W3C graphics standards ecosystem includes related work covering
masking, compositing/blending, transforms, filter effects, geometry
interfaces, and color.

Implementation consequence:

-   treat these as compatibility references for corresponding projection
    features;
-   do not create internal architecture by copying their document
    structures.

## a.3 css color

Current CSS Color work includes color syntax and color-space
capabilities beyond historical sRGB-only usage.

Implementation consequence:

-   architect color so richer spaces can be represented/projected later;
-   gate actual emitted syntax by compatibility profile.

## a.4 harfbuzz

HarfBuzz is a mature text-shaping engine. Its shaping operation maps
Unicode input to positioned glyphs using font, direction, script,
language, and feature information.

Implementation consequence:

-   use it as an optional shaping backend when exact glyph layout is
    required;
-   do not duplicate script-specific shaping algorithms inside the svg
    compiler.

## a.5 pathkit / skia

Skia PathKit provides a plausible mature boundary for sophisticated path
operations in environments where its deployment model is acceptable.

Implementation consequence:

-   isolate it behind canonical path input/output;
-   do not require it for basic svg compilation.

## a.6 resvg/usvg family

The resvg/usvg ecosystem demonstrates the value of preprocessing and
normalization before rendering and provides a potential independent
static-svg raster/compatibility boundary.

Implementation consequence:

-   optional focused validation/raster adapter;
-   do not treat its supported static subset as the complete definition
    of svg capability.

------------------------------------------------------------------------

# appendix b --- authority-safe dependency decision template

Before adding any external dependency, record internally:

``` text
capability required:
existing savant capability:
stdlib capability:
candidate:
upstream:
license:
maintenance evidence:
security/supply-chain considerations:
determinism impact:
lineage/provenance impact:
replay impact:
deployment cost:
fallback behavior:
architectural boundary:
decision: adopt / reject / defer
reason:
```

Only material decisions need durable recording.

------------------------------------------------------------------------

# appendix c --- semantic example

``` python
scene = Scene(
    view_box=ViewBox(0, 0, 1920, 1080),
    children=[
        Group(
            name="primary-composition",
            children=[
                Instance(
                    component=ornament,
                    transform=Transform.translate(420, 540),
                ),
                Instance(
                    component=ornament,
                    transform=(
                        Transform.translate(960, 540)
                        @ Transform.rotate(0.42)
                        @ Transform.scale(1.35)
                    ),
                ),
                Instance(
                    component=ornament,
                    transform=(
                        Transform.translate(1500, 540)
                        @ Transform.rotate(-0.31)
                        @ Transform.scale(0.92)
                    ),
                ),
            ],
            clip=ClipPath(
                children=[
                    RoundedRectangle(
                        x=120,
                        y=100,
                        width=1680,
                        height=880,
                        radius=80,
                    ),
                ],
            ),
            mask=Mask(
                mode="luminance",
                children=[
                    Circle(
                        center=Point(960, 540),
                        radius=760,
                        fill=RadialGradient(
                            stops=[
                                Stop(0.0, Color.white()),
                                Stop(0.72, Color.white()),
                                Stop(1.0, Color.black()),
                            ],
                        ),
                    ),
                ],
            ),
            filter=FilterGraph(
                primitives=[
                    Turbulence(
                        base_frequency=(0.012, 0.018),
                        octaves=3,
                        seed=17,
                        result="noise",
                    ),
                    DisplacementMap(
                        source=SourceGraphic,
                        displacement="noise",
                        scale=18,
                        result="displaced",
                    ),
                    GaussianBlur(
                        source="displaced",
                        std_deviation=0.65,
                        result="softened",
                    ),
                    ColorMatrix(
                        source="softened",
                        matrix=...,
                    ),
                ],
            ),
            blend_mode="multiply",
        ),
    ],
)
```

The caller never writes `<defs>`, chooses generated mask IDs, or
manually topologically orders filter dependencies.

------------------------------------------------------------------------

# appendix d --- migration packet relationship

This task follows the current bounded migration work.

Execution sequence:

``` text
sdump maximum-evolution
→ compact migration dump proof
→ migration packet finalization
→ savant svg renderer enterprise implementation
```

If development moves to a new ChatGPT Project before implementation
begins, this file should accompany the newest compact sdump, masterplan,
and structure reference documents or be explicitly referenced by the new
masterplan.

------------------------------------------------------------------------

# appendix e --- final task state

specification_state: complete\
implementation_state: not_started\
validation_state: not_applicable_until_implementation\
next_action_when_activated: resolve current savant renderer ownership
with minimum inspection, then implement the durable kernel directly\
completion_definition: all applicable enterprise gates in this document
pass with minimum sufficient evidence
