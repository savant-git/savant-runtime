# Cinematic Intro Validation Report

Validated: 2026-07-16 UTC on branch `codex/savant-cinematic-logo-reveal`.

## Executive result

The isolated React frontend contains an 18.5-second, five-act, deterministic R3F/Three.js intro, a GSAP master timeline, concurrent landing-page readiness, semantic entry/skip/audio controls, renderer and missing-asset recovery, reduced-motion playback, persistent one-time entry, capability tiers, and a one-way frame-time quality downgrade. It does not invent a logo when the approved source is absent.

Brand-accurate Definition of Done is **not met**: no approved Savant SVG or GLB exists in the repository. Native-device GPU profiling, browser automation, visual-regression captures, and authored/licensed audio stems are also unavailable in this environment. The fallback wordmark is explicitly not represented as the approved mark.

## Safety and replacement boundary

- Protected sibling `/root/savant-runtime` was not inspected or changed.
- No credentials or environment files were inspected.
- No deployment command was run.
- The baseline commit contains no tracked browser frontend; `frontend/` and these documents were untracked work at audit time.
- No Python runtime, canon, service, route, symlink, or unrelated repository file was changed.
- Changes are confined to `frontend/` and `docs/cinematic-intro/`.

## Architecture delivered

```text
index.html -> main.tsx -> App
                         |-- LandingPage (mount + font readiness)
                         `-- lazy CinematicIntro
                              |-- reducer state machine
                              |-- capability + quality selection
                              |-- GSAP master timeline / audio cues
                              |-- semantic DOM controls + transition
                              `-- lazy R3F Canvas
                                   |-- data-driven camera + lighting
                                   |-- five independent act scenes
                                   |-- adaptive frame governor
                                   `-- tiered postprocessing
```

State flow:

```text
booting -> capabilityCheck -> loadingCritical -> readyToPlay -> playing
   \             \                 \                 \          \
    +-------------+-----------------+-----------------+----------> recoverableError
                                                               
playing -> cinematicComplete -- appReady --> awaitingEntry
   |              ^                               |
   +-- appReady --+                               v
                                           transitioning -> entered
```

`ENTER SAVANT` is derived from `cinematicComplete && appReady && !entryRequested`. A reducer guard prevents double activation. Renderer failure exposes direct entry. Missing secondary assets settle rather than leaving a permanent loading state.

## Dependencies

- Runtime: React 19, React DOM 19, Three.js 0.185, React Three Fiber 9, GSAP 3, postprocessing, React Three Postprocessing.
- Development: TypeScript 5.8, Vite 7, Vitest 3, Testing Library, ESLint 9, Prettier 3, glTF Transform CLI.
- Removed in this pass: `@react-three/drei`; its single GLTF abstraction was replaced by `GLTFLoader` to reduce production weight.
- Production dependency audit: 0 known vulnerabilities.

## Files

Added/reworked under `frontend/`: package/config/lock files, HTML entry, `src/App.tsx`, `src/main.tsx`, landing page and global styles; cinematic orchestration, reducer, capability detector, quality selector/governor, asset manifest, timeline, transition controller, audio controller, error/fallback components, data-driven camera/lighting/postprocessing, five act scenes, deterministic particle helper, debug panel, and 27 tests. Build output in `frontend/dist/` was regenerated.

Documentation: `EXISTING_INTRO_AUDIT.md`, `CINEMATIC_ARCHITECTURE.md`, `ASSET_INVENTORY.md`, `PERFORMANCE_BUDGET.md`, `SHOT_LIST.md`, and this report. No file was moved or deleted outside those boundaries.

## Validation results

| Check | Result |
| --- | --- |
| TypeScript | pass |
| ESLint | pass |
| Prettier | pass |
| Vitest | 4 files, 27 tests pass |
| Production build | pass, Vite 7.3.6 |
| Production dependency audit | pass, 0 vulnerabilities |
| Production preview | HTTP 200 on local preview |
| Missing logo | request resolves to HTML fallback; MIME validation rejects it correctly and runtime continues |
| Browser screenshots | not run; no Chromium/Playwright executable available |
| Android hardware | not run; capability/mobile logic unit-tested, native GPU performance unverified |

Tests cover startup order, readiness in either order, button gating, repeated activation, skip semantics, renderer recovery, retry, direct entry, reduced motion, monotonic progress, one-way quality downgrade, persisted route entry, missing/network-failed logo, and quality selection.

## Production bundle measurement

| Output | Raw | Gzip |
| --- | ---: | ---: |
| Initial app route | 181.17 kB | 57.24 kB |
| React vendor | 3.70 kB | 1.42 kB |
| Cinematic vendor | 905.35 kB | 245.38 kB |
| Cinematic canvas | 55.86 kB | 17.92 kB |
| Cinematic orchestration | 80.08 kB | 31.78 kB |
| Postprocessing | 178.24 kB | 78.97 kB |
| CSS | 6.74 kB | 2.49 kB |

The cinematic vendor chunk meets its 260 kB gzip budget after removing Drei, but aggregate lazy cinematic transfer exceeds that single-chunk budget once orchestration and postprocessing are included. Vite still reports the raw Three vendor chunk above 500 kB. No runtime FPS, 1% low, GPU memory, draw-call, or replay-memory values are claimed without browser instrumentation.

## Accessibility and fallbacks

- Semantic buttons, 44-54 px targets, focus-visible treatment, keyboard activation, screen-reader status/progress, and focus transfer to the landing page.
- Reduced-motion preference uses a 3.5-second camera-stable reveal while preserving readiness gating.
- Skip appears after two seconds and never fakes app readiness.
- WebGL 2 failure selects the DOM essential fallback; context loss selects recoverable fallback.
- Audio starts muted, requires a user gesture, and never gates playback or entry.
- Session storage failure cannot block entry.
- Essential fallback and direct entry prevent a permanent black screen.

## Commands

```bash
cd /root/savant-runtime-2/frontend
npm install
npm run dev
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm run preview
```

Asset inspection and optimization after an approved GLB is supplied:

```bash
npm run asset:inspect
npm run asset:optimize
```

No deployment target or deploy command is defined; deployment must not be inferred.

## Candid visual assessment

Achieved in real time: deterministic atmospheric depth, intentional signal, recurring instanced fracture language, material-state changes, a connected computational lattice, convergence pressure wave, controlled camera choreography, motivated cool/warm lighting, restrained tiered postprocessing, a final recognition hold, and continuous DOM-to-site transition.

Requires external authored input or hardware validation: the actual approved logo reveal, logo topology/bevel/material inspection, authored micro-surface textures/HDR environment, original licensed sound stems, film-quality volumetrics, native Moto G measurements, and deterministic story-beat screenshots. Those limitations cannot be truthfully replaced with generated placeholders or desktop assumptions.
