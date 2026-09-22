# Cinematic Asset Inventory

## Discovery inventory

No browser image, texture, model, logo, font, audio, shader, environment, HTML, or public asset was present in `/root/savant-runtime-2` at discovery.

| Asset class | Source found | Status |
| --- | --- | --- |
| Approved Savant logo | None | Blocking brand-accuracy completion; no invented substitute is rendered |
| 3D models | None | Procedural geometry planned |
| Textures/HDRI | None | Procedural/custom environment planned |
| Fonts | None | System stack initially; optional licensed WOFF2 may be added later |
| Audio | None | Architecture only until original/licensed sources are supplied |
| Shaders | None | New source shaders will be repository-owned |

## Runtime manifest contract

| Source path | Runtime path | Format | Tier | Validation |
| --- | --- | --- | --- | --- |
| `frontend/assets/source/savant-logo-approved.svg` or `.glb` | `frontend/public/cinematic/savant-logo.glb` | GLB 2.0 | all | Missing; must preserve approved proportions |
| Procedural environment | generated in code | geometry/shader | all | No transfer asset |
| Original audio stems | `frontend/assets/source/audio/` | WAV source | optional | Missing; muted visual experience required |
| Optimized audio | `frontend/public/cinematic/audio/` | OGG/MP3 | standard/ultra | Missing until licensed source exists |

## Approved-logo pipeline (to run after source is supplied)

```bash
cd frontend
npx @gltf-transform/cli inspect assets/source/savant-logo.glb
npx @gltf-transform/cli optimize assets/source/savant-logo.glb public/cinematic/savant-logo.glb --compress meshopt --texture-compress webp
npx @gltf-transform/cli inspect public/cinematic/savant-logo.glb
```

If the approved source is SVG, a deterministic Blender conversion script must be added rather than manually tracing or redesigning the mark. The source remains preserved under `assets/source/`.

## Acceptance report fields

The final asset validator will report path, bytes, bounds, orientation, vertex and triangle count, meshes, materials, textures, animation tracks, extensions, draw-call implications, tier, and result. Values cannot be truthfully populated before an approved asset exists.
