# Cinematic Architecture

## Decision

Create an isolated React 19 + TypeScript + Vite package using Three.js, React Three Fiber, GSAP for the master timeline, and `@react-three/postprocessing` for restrained screen-space passes. Drei was removed after measurement because the only abstraction used was GLTF loading; Three's native `GLTFLoader` is smaller and equally maintainable here. WebGL 2 is the production baseline. WebGPU is capability-reported but not selected for the initial renderer because the required postprocessing and R3F integration have more predictable production behavior on WebGL 2; this avoids two divergent rendering implementations.

Babylon.js was rejected because no existing frontend favors it and mixing engines would add bundle, lifecycle, and shader complexity. Native Three.js without React was rejected because the new landing shell benefits from React's error boundaries, accessibility controls, readiness orchestration, and test ecosystem.

## Package boundary

`frontend/` is self-contained. It does not import Python files, follow repository symlinks, or require Palaver for entry.

## Modules

```text
frontend/src/cinematic/
  CinematicIntro.tsx
  CinematicCanvas.tsx
  CinematicErrorBoundary.tsx
  config/{assets,cinematic,postprocessing,quality,shots}.ts
  state/machine.ts
  capability/detectCapabilities.ts
  quality/selectQualityTier.ts
  timeline/createMasterTimeline.ts
  transition/useEntryTransition.ts
  audio/CinematicAudioController.ts
  scenes/{UnformedSignal,Fracture,SavantAwakening,LogoForge,FinalRecognition}.tsx
  camera/CinematicCamera.tsx
  lighting/CinematicLighting.tsx
  materials/
  particles/
  shaders/
  hooks/
  tests/
```

Timing, shots, quality, assets, and postprocessing are typed centralized configuration. Render loops mutate refs/uniforms, never per-frame React state.

## Startup state machine

```text
booting -> capabilityCheck -> loadingCritical -> readyToPlay -> playing
    |              |               |                 |          |
    +--------------+---------------+-----------------+----------v
                         recoverableError       cinematicComplete
                                                       |
                            appReady -------------------+
                                                       v
                                                 awaitingEntry
                                                       |
                                                 transitioning
                                                       |
                                                    entered
```

Independent facts are tracked for cinematic assets, application readiness, timeline completion, and entry choice. `ENTER SAVANT` is derived only when timeline complete AND app ready. A finite timeout selects a fallback; it does not fake asset success. Skip accelerates to an elegant final state but still respects application readiness.

## Website readiness

For this new package, `appReady` means:

1. React landing route has mounted.
2. Critical landing content has committed.
3. Fonts have settled or timed out to system fallbacks.
4. Cinematic logo source has loaded or the explicit essential fallback has been selected.
5. No fatal app initialization error exists.

## Renderer lifecycle

- Canvas is lazy-loaded after capability selection.
- A renderer error boundary activates semantic DOM fallback controls.
- Rendering pauses when `document.hidden`.
- The Canvas unmounts after entry.
- GSAP contexts, timers, observers, listeners, audio nodes, and WebGL resources are cleaned up.
- Replay remounts one canvas and resets deterministic seeds.

## Quality strategy

Quality is selected from measured capabilities: WebGL 2, device memory when exposed, hardware concurrency, max texture size, renderer limits, DPR, reduced motion, and an initial frame-time sample. Selection is sticky for the session. It never relies only on a user agent or viewport width.

## Failure model

- Missing approved logo: use clearly documented accessible fallback wordmark and allow entry.
- Renderer failure/WebGL unavailable: use a five-beat CSS/canvas-lite fallback.
- Individual secondary asset failure: omit layer and continue.
- Critical load timeout: show recovery message, retry, and direct-entry control.
- Audio blocked: remain muted; never block playback or entry.

## Debug architecture

Development-only controls return `null` unless both `import.meta.env.DEV` and the `cinematicDebug` query flag are present. Vite replaces the production flag at build time. The panel supports act jumps, pause/resume, and replay; full automated capture remains pending a browser-test executable.
