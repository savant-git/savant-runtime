# Performance Budget

## Transfer and parse budgets

| Metric | Ultra | Standard | Mobile | Essential fallback |
| --- | ---: | ---: | ---: | ---: |
| Lazy cinematic JS gzip | 260 KB | same chunk | same chunk | <= 35 KB additional |
| Approved logo GLB | 1.5 MB | 900 KB | 500 KB | approved SVG/wordmark <= 80 KB |
| Textures | 4 MB | 2 MB | 800 KB | 0-200 KB |
| Audio | 2.5 MB optional | 1.5 MB optional | off by default | none |
| Initial app route JS gzip | 180 KB | 180 KB | 180 KB | 180 KB |

## Runtime budgets

| Metric | Ultra | Standard | Mobile |
| --- | ---: | ---: | ---: |
| Target FPS | 60 | 45-60 | stable >= 30 |
| DPR ceiling | 2.0 | 1.5 | 1.0 |
| Draw calls | <= 90 | <= 65 | <= 38 |
| Visible triangles | <= 750k | <= 400k | <= 180k |
| GPU particles | 50k | 22k | 7k |
| Dynamic shadow lights | 2 | 1 | 0-1 |
| Shadow map | 2048 | 1024 | 512/off |
| Transparent full-screen layers | <= 3 | <= 2 | <= 1 |
| Active post passes | <= 6 | <= 4 | <= 2 |
| Main-thread long task | none > 100 ms | none > 100 ms | none > 150 ms |

## Tier changes

Selection occurs once before playback. A startup frame sampler may downgrade one tier after sustained frame time above 28 ms; it cannot upgrade or oscillate during playback. Reduced motion selects a specialized short path, not merely lower quality.

## Measurement protocol

- Chromium desktop, fixed 1440x900 and DPR 1.
- Mobile emulation, 412x915 and DPR 1, 4x CPU throttle when available.
- Deterministic seed and named timeline markers.
- Record median and 1% low FPS, renderer info, draw calls, triangles, geometries, textures, JS/asset bytes, readiness times, and replay cleanup.

Baseline frontend metrics are “not applicable” because no frontend existed at discovery.

## Measured production build — 2026-07-16

The Three/R3F vendor chunk is 245.38 kB gzip (within the 260 kB individual-chunk budget). Canvas code is 17.92 kB gzip, orchestration 31.78 kB gzip, and postprocessing 78.97 kB gzip. Aggregate lazy cinematic transfer therefore exceeds the original 260 kB interpretation and remains an optimization target. Initial route code is 57.24 kB gzip. Runtime frame, draw-call, triangle, texture, and memory measurements require a browser/GPU profiler and are not fabricated here.
