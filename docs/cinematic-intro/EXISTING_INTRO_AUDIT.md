# Existing Intro Audit

## Audit boundary

- Repository: `/root/savant-runtime-2`
- Branch: `codex/savant-cinematic-logo-reveal`
- Baseline commit: `baddebd`
- Discovery date: 2026-07-15 UTC
- Protected sibling `/root/savant-runtime` was not inspected.
- Legacy symlinks, including `webui_ultra`, were not followed because their targets may cross the protected boundary.

## Finding at baseline commit

There is no **tracked** frontend, loading screen, preloader, landing route, browser entry point, logo reveal, or website implementation in the baseline commit. The tracked project is a Python 3.10+ filesystem/canon runtime with a Flask Palaver service. At the 2026-07-16 continuation audit, `frontend/` and `docs/cinematic-intro/` were present as untracked replacement work and were preserved, audited, corrected, and validated rather than treated as tracked legacy code.

Therefore there is no old intro code that can safely be removed and no caller/import/route graph to replace. The cinematic implementation will be introduced as a new, isolated `frontend/` package. Existing Python, canon, runtime, scripts, tests, symlinks, and services remain untouched.

## Existing architecture

| Concern | Existing implementation |
| --- | --- |
| Runtime | Python 3.10+, setuptools |
| Service | Flask 3.1.3 + flask-cors |
| Canon tooling | `canon-system/runtime/canonctl.py` |
| Browser framework | None |
| Bundler | None |
| Router | None |
| Hydration/entry | None |
| 3D/animation | None |
| Loading state | None |
| Logo assets | None in repository |
| Fonts/audio/shaders | None for browser use |
| Browser tests | None |
| Deployment target | Not defined for a frontend |

## Startup trace

No HTML-to-hydration flow exists. The documented runtime flow is Python-only:

1. Install the package with setuptools.
2. Optionally start `palaver_voice_backend.py`.
3. Flask exposes Palaver endpoints with explicit environment configuration.

The new frontend must not assume that the Flask service is available for first paint or entry. App readiness is defined locally as: React mounted, landing content committed, critical CSS loaded, approved logo asset settled (loaded or fallback selected), and no fatal startup error.

## Existing checks and baseline

| Command | Baseline result |
| --- | --- |
| `.venv/bin/python -m unittest discover -s tests -v` | Failed: 2 pass, 3 errors; Flask missing and canon subprocess checks fail in temp copies |
| `.venv/bin/python canon-system/runtime/canonctl.py validate` | Failed: `jsonschema` missing in existing venv |
| `.venv/bin/ruff check .` | Failed: 108 pre-existing findings |
| `.venv/bin/mypy ...` | Not runnable: mypy absent from existing venv |

These results are recorded, not repaired, because unrelated runtime modernization is outside the cinematic scope.

## Replacement boundary

Allowed additions are limited to:

- `frontend/` and its package-local configuration, source, tests, and assets.
- `docs/cinematic-intro/`.
- A small root README note only if needed for discoverability.

No existing intro files will be deleted because none exist. No runtime route, Python module, canon record, service configuration, or legacy symlink will be changed.

## Critical blocker

No approved Savant logo source exists in scope. The implementation may provide a clearly marked development fallback wordmark, but Definition of Done for the approved mark cannot be claimed until an approved SVG/GLB is placed at the documented manifest path. The fallback must never be represented as the approved logo.
